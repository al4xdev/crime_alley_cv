from __future__ import annotations

import re
import secrets
from pathlib import Path
from typing import Any

from .capture import data_root
from .io import atomic_write_json, read_json_object
from .models import ConversationEnvelope, HumanLabel


def _contained(root: Path, *parts: str) -> Path:
    candidate = root.joinpath(*parts).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError("Label path escapes the Celestial label root")
    return candidate


def _pii_values(initial_cv: str) -> list[str]:
    values = re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", initial_cv)
    values += re.findall(r"https?://[^\s)>]+", initial_cv)
    values += re.findall(r"(?:\+?\d[\d ().-]{7,}\d)", initial_cv)
    first_heading = next(
        (
            line.removeprefix("#").strip()
            for line in initial_cv.splitlines()
            if line.startswith("#")
        ),
        "",
    )
    if len(first_heading) >= 3:
        values.append(first_heading)
    return sorted(set(values), key=len, reverse=True)


def _redact(content: str, pii: list[str]) -> str:
    redacted = content
    for index, value in enumerate(pii, 1):
        redacted = re.sub(re.escape(value), f"[CANDIDATE_PII_{index}]", redacted, flags=re.I)
    return redacted


def _cv_claims(content: str) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    for line in content.splitlines():
        text = line.strip()
        if not text or text.startswith("#") or set(text) <= {"-", "_", "*"}:
            continue
        text = re.sub(r"^(?:[-*+] |\d+[.)] )", "", text).strip()
        if text:
            claims.append({"claim_id": f"claim-{len(claims) + 1:03d}", "text": text})
    return claims[:250]


def export_blind_tasks(benchmark_root: Path, output: Path) -> Path:
    manifest = read_json_object(benchmark_root / "manifest.json")
    if manifest.get("schema_version") != 2:
        raise ValueError("Celestial v1 benchmarks are audit-only")
    case_root = data_root() / "cases" / str(manifest["case_id"])
    initial_cv = (case_root / "inputs" / "initial_cv.md").read_text(encoding="utf-8")
    pii = _pii_values(initial_cv)
    human_root = benchmark_root / "human"
    private_path = human_root / "private-map.json"
    if private_path.exists():
        private_map = read_json_object(private_path)
    else:
        private_map = {"schema_version": 2, "benchmark_id": manifest["benchmark_id"], "items": {}}
    mappings = private_map["items"]
    if not isinstance(mappings, dict):
        raise ValueError("Invalid private human-task map")

    by_role: dict[str, list[Path]] = {}
    for path in sorted((case_root / "envelopes").glob("*/*.json")):
        envelope = ConversationEnvelope.model_validate_json(path.read_text())
        if envelope.status.value == "observed":
            by_role.setdefault(envelope.role.value, []).append(path)
    tasks: list[dict[str, Any]] = []

    def blind_id(key: str) -> str:
        existing = mappings.get(key)
        if isinstance(existing, dict) and isinstance(existing.get("blind_item_id"), str):
            return str(existing["blind_item_id"])
        identifier = "task-" + secrets.token_hex(12)
        mappings[key] = {"blind_item_id": identifier}
        return identifier

    for role, paths in sorted(by_role.items()):
        envelope = ConversationEnvelope.model_validate_json(paths[-1].read_text())
        key = f"role:{role}:{envelope.invocation}"
        identifier = blind_id(key)
        mappings[key]["canonical_item_id"] = f"{role}-{envelope.invocation:03d}"
        tasks.append(
            {
                "blind_item_id": identifier,
                "kind": "role_scoring",
                "role": role,
                "messages": [
                    {
                        **message.model_dump(mode="json"),
                        "content": _redact(message.content, pii),
                    }
                    for message in envelope.messages
                ],
            }
        )

    def add_pair(key: str, before: str, after: str, kind: str) -> None:
        identifier = blind_id(key)
        mapping = mappings[key]
        if "swapped" not in mapping:
            mapping["swapped"] = bool(secrets.randbelow(2))
        swapped = bool(mapping["swapped"])
        a, b = (after, before) if swapped else (before, after)
        mapping["preferred_revision_side"] = "a" if swapped else "b"
        tasks.append(
            {
                "blind_item_id": identifier,
                "kind": kind,
                "candidate_a": _redact(a, pii),
                "candidate_b": _redact(b, pii),
            }
        )

    for path in by_role.get("bill", []):
        envelope = ConversationEnvelope.model_validate_json(path.read_text())
        messages = {message.source_label: message.content for message in envelope.messages}
        if "cv_before" in messages and "cv_after" in messages:
            add_pair(
                f"bill_pair:{envelope.invocation}",
                messages["cv_before"],
                messages["cv_after"],
                "revision_pair",
            )
    add_pair(
        "baseline_final",
        (benchmark_root / "baseline" / "cv.md").read_text(encoding="utf-8"),
        (case_root / "inputs" / "final_cv.md").read_text(encoding="utf-8"),
        "baseline_final_pair",
    )

    for claim_set, content in (
        ("baseline", (benchmark_root / "baseline" / "cv.md").read_text(encoding="utf-8")),
        ("final", (case_root / "inputs" / "final_cv.md").read_text(encoding="utf-8")),
    ):
        key = f"cv_claims:{claim_set}"
        identifier = blind_id(key)
        mappings[key]["claim_set"] = claim_set
        claims = _cv_claims(content)
        tasks.append(
            {
                "blind_item_id": identifier,
                "kind": "cv_claim_validation",
                "reference_material": {
                    "initial_cv": _redact(initial_cv, pii),
                    "job_description": _redact(
                        (case_root / "inputs" / "job_description.md").read_text(
                            encoding="utf-8"
                        ),
                        pii,
                    ),
                },
                "claims": [
                    {**claim, "text": _redact(claim["text"], pii)} for claim in claims
                ],
            }
        )

    for item_root in sorted((benchmark_root / "items").glob("*")):
        result_path = item_root / "result-01.json"
        if not result_path.is_file():
            continue
        result = read_json_object(result_path)
        result_claims = result.get("claims")
        if not isinstance(result_claims, list) or not result_claims:
            continue
        key = f"claims:{item_root.name}"
        identifier = blind_id(key)
        mappings[key]["canonical_item_id"] = item_root.name
        tasks.append(
            {
                "blind_item_id": identifier,
                "kind": "claim_validation",
                "claims": [
                    {
                        "claim_id": claim["claim_id"],
                        "text": _redact(str(claim["text"]), pii),
                    }
                    for claim in result_claims
                    if isinstance(claim, dict)
                ],
            }
        )
    atomic_write_json(private_path, private_map)
    payload = {
        "schema_version": 2,
        "benchmark_id": manifest["benchmark_id"],
        "minimum_raters_per_item": 2,
        "instructions": (
            "Score content only. Candidate PII, provider, model, run and A/B order are hidden."
        ),
        "tasks": tasks,
    }
    atomic_write_json(human_root / "tasks.json", payload)
    atomic_write_json(output, payload)
    return output


def import_label(path: Path) -> Path:
    label = HumanLabel.model_validate_json(path.read_text(encoding="utf-8"))
    benchmark_root = _contained(data_root() / "benchmarks", label.benchmark_id)
    tasks_path = benchmark_root / "human" / "tasks.json"
    if not tasks_path.is_file():
        raise ValueError("Export blind tasks before importing labels")
    tasks = read_json_object(tasks_path).get("tasks")
    task_by_id = (
        {
            str(task.get("blind_item_id")): task
            for task in tasks
            if isinstance(task, dict) and isinstance(task.get("blind_item_id"), str)
        }
        if isinstance(tasks, list)
        else {}
    )
    task = task_by_id.get(label.blind_item_id)
    if task is None:
        raise ValueError("Human label references an unknown blind task")
    kind = task.get("kind")
    if kind == "role_scoring":
        if label.instruction_scores is None or label.pairwise_preference or label.claim_support:
            raise ValueError("Role-scoring tasks require only both score panels")
    elif kind in {"revision_pair", "baseline_final_pair"}:
        if (
            label.pairwise_preference is None
            or label.instruction_scores is not None
            or label.claim_support
        ):
            raise ValueError("Pairwise tasks require only an A/B preference")
    elif kind in {"claim_validation", "cv_claim_validation"}:
        claims = task.get("claims")
        expected_claim_ids = {
            str(claim.get("claim_id"))
            for claim in claims
            if isinstance(claim, dict) and isinstance(claim.get("claim_id"), str)
        } if isinstance(claims, list) else set()
        if (
            label.claim_support is None
            or set(label.claim_support) != expected_claim_ids
            or label.instruction_scores is not None
            or label.pairwise_preference
        ):
            raise ValueError("Claim tasks require a label for every registered claim")
    else:
        raise ValueError("Human label references an unsupported task kind")
    root = _contained(data_root() / "labels", label.benchmark_id)
    destination = _contained(root, f"{label.blind_item_id}-{label.rater_id}.json")
    atomic_write_json(destination, label.model_dump(mode="json"), exclusive=True)
    return destination
