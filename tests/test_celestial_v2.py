from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from the_celestial.benchmark import generate_baseline, plan_capture, run_benchmark
from the_celestial.capture import (
    create_run_request,
    freeze_capture,
    record_case_input,
    record_envelope,
    update_request,
    verify_frozen_case,
)
from the_celestial.labels import export_blind_tasks, import_label
from the_celestial.metrics import build_report
from the_celestial.models import DIMENSIONS, AgentRole, VerificationRequest
from the_celestial.provider import ProviderCapabilityError, run_prompt
from the_celestial.verification import collect_frozen_excerpts


def _capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, evidence: Path | None = None
) -> str:
    monkeypatch.setenv("CELESTIAL_DATA_DIR", str(tmp_path / "celestial"))
    create_run_request(
        capture_id="capture-v2",
        run_id="run-v2",
        run_dir="/not-exposed",
        subject_provider="claude",
        subject_model="claude-sonnet-4-20250514",
        celestial_requested=True,
        judge_provider="codex",
        judge_model="gpt-5.4",
    )
    record_case_input(
        "capture-v2",
        "initial_cv",
        "# Alice Example\n\nalice@example.com\n\n- Built reliable Python services.\n",
    )
    record_case_input("capture-v2", "job_description", "# Platform Engineer\n\nBuild services.\n")
    record_case_input(
        "capture-v2",
        "final_cv",
        "# Alice Example\n\n- Built reliable Python services.\n- Improved documentation.\n",
    )
    record_envelope(
        capture_id="capture-v2",
        run_id="run-v2",
        role=AgentRole.KAREN,
        invocation=1,
        instruction=("karen_instruction", "Assess only supplied CV evidence."),
        inputs={"candidate_cv": "# Alice Example\n\nBuilt Python services."},
        outputs={"evaluation_report": "# Evaluation\n\nThe experience is relevant."},
    )
    update_request("capture-v2", status="capture_complete")
    case = freeze_capture(
        "capture-v2", evidence_roots=[evidence] if evidence is not None else None
    )
    update_request("capture-v2", status="ready")
    return case.name


def _evaluation(prompt: str, *, invalid_citation: bool = False) -> str:
    match = re.search(
        r"REQUIRED RESULT METADATA\n(\{.*?\})\n\nAVAILABLE VERIFICATION",
        prompt,
        re.S,
    )
    assert match is not None
    metadata = json.loads(match.group(1))
    message_id = "unknown-message" if invalid_citation else "output-1"
    panel = {
        "dimensions": {
            dimension: {
                "score": 3,
                "rationale": "The supplied content is clear and grounded.",
                "message_ids": [message_id],
            }
            for dimension in DIMENSIONS
        },
        "index_100": 75.0,
    }
    return json.dumps(
        {
            "schema_version": 2,
            **metadata,
            "instruction_design": panel,
            "execution_and_output": panel,
            "global_index_100": 75.0,
            "claims": [
                {
                    "claim_id": "claim-1",
                    "text": "The output discusses relevant experience.",
                    "message_ids": [message_id],
                    "status": "supported",
                    "severity": "low",
                }
            ],
            "verification_requests": [],
            "strengths": ["Relevant content"],
            "risks": [],
            "confidence": 0.8,
        }
    )


def _fake_provider(calls: list[str]) -> Callable[..., str]:
    def fake(provider: str, model: str, prompt: str, **_: Any) -> str:
        calls.append(prompt)
        if prompt.startswith("Revise the candidate CV"):
            return (
                "# Alice Example\n\n## Summary\n\nReliable platform engineer.\n\n"
                "## Experience\n\n- Built reliable Python services.\n"
                "- Added an invented certification.\n"
            )
        if prompt.startswith("Compare only the two CVs"):
            return json.dumps(
                {"preference": "a", "rationale": "A is clearer.", "confidence": 0.8}
            )
        return _evaluation(prompt)

    return fake


def _completed_benchmark(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, list[str], str]:
    case_id = _capture(tmp_path, monkeypatch)
    calls: list[str] = []
    monkeypatch.setattr("the_celestial.benchmark.run_prompt", _fake_provider(calls))
    plan = plan_capture("capture-v2")
    digest = str(plan["plan_digest"])
    generate_baseline("capture-v2", digest)
    root = run_benchmark("capture-v2", plan_digest=digest)
    return root, calls, case_id


def test_benchmark_is_immutable_idempotent_and_does_not_mutate_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, calls, case_id = _completed_benchmark(tmp_path, monkeypatch)
    before = verify_frozen_case(case_id)["digest"]
    assert len(calls) == 10

    run_benchmark(
        "capture-v2",
        plan_digest=json.loads((root / "spec.json").read_text())["plan_digest"],
    )

    assert len(calls) == 10
    assert verify_frozen_case(case_id)["digest"] == before
    assert len(list((root / "items").glob("*/result-*.json"))) == 6


def test_failed_evaluation_resumes_with_a_new_raw_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _capture(tmp_path, monkeypatch)
    calls: list[str] = []
    valid = _fake_provider(calls)
    invalid_outputs = 2

    def flaky(provider: str, model: str, prompt: str, **kwargs: Any) -> str:
        nonlocal invalid_outputs
        calls.append(prompt)
        if prompt.startswith("Revise the candidate CV"):
            return valid(provider, model, prompt, **kwargs)
        if invalid_outputs and "REQUIRED RESULT METADATA" in prompt:
            invalid_outputs -= 1
            return "{}"
        return valid(provider, model, prompt, **kwargs)

    monkeypatch.setattr("the_celestial.benchmark.run_prompt", flaky)
    plan = plan_capture("capture-v2")
    digest = str(plan["plan_digest"])
    generate_baseline("capture-v2", digest)
    with pytest.raises(RuntimeError, match="resume"):
        run_benchmark("capture-v2", plan_digest=digest)
    root = tmp_path / "celestial" / "benchmarks" / str(plan["benchmark_id"])
    assert not (root / "manifest.json").exists()

    run_benchmark("capture-v2", plan_digest=digest)

    assert (root / "manifest.json").is_file()
    assert list((root / "items").glob("*/raw/01-attempt-02-initial.txt"))
    ledger = [json.loads(line) for line in (root / "ledger.jsonl").read_text().splitlines()]
    assert [event["sequence"] for event in ledger] == list(range(1, len(ledger) + 1))
    assert all("event_sha256" in event for event in ledger)


def test_invalid_citations_are_repaired_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _capture(tmp_path, monkeypatch)
    calls: list[str] = []

    def provider(_: str, __: str, prompt: str, **___: Any) -> str:
        calls.append(prompt)
        if prompt.startswith("Revise the candidate CV"):
            return _fake_provider([])("claude", "model", prompt)
        if prompt.startswith("Compare only the two CVs"):
            return json.dumps({"preference": "a", "rationale": "clear", "confidence": 0.5})
        return _evaluation(
            prompt,
            invalid_citation="prior response was invalid" not in prompt.casefold(),
        )

    monkeypatch.setattr("the_celestial.benchmark.run_prompt", provider)
    plan = plan_capture("capture-v2")
    digest = str(plan["plan_digest"])
    generate_baseline("capture-v2", digest)
    root = run_benchmark("capture-v2", plan_digest=digest)

    assert len(list((root / "items").glob("*/raw/*-repair.txt"))) == 6
    assert all(
        "unknown-message" not in path.read_text()
        for path in (root / "items").glob("*/result-*.json")
    )


def test_verification_is_limited_to_frozen_exact_sources_without_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "evidence.md").write_text("Unique verified phrase.")
    (repository / "secret.bin").write_bytes(b"not collected")
    case_id = _capture(tmp_path, monkeypatch, evidence=repository)
    case_root = tmp_path / "celestial" / "cases" / case_id
    manifest = json.loads((case_root / "manifest.json").read_text())
    source_id = manifest["evidence_entries"][0]["source_id"]

    missing = collect_frozen_excerpts(
        case_root,
        [VerificationRequest(claim_id="claim-1", source_id=source_id, query="absent phrase")],
    )
    found = collect_frozen_excerpts(
        case_root,
        [VerificationRequest(claim_id="claim-1", source_id=source_id, query="verified phrase")],
    )

    assert missing[0]["status"] == "unavailable" and missing[0]["excerpt"] == ""
    assert found[0]["status"] == "available"
    assert all(entry["relative_path"] != "secret.bin" for entry in manifest["evidence_entries"])


def test_blind_labels_redact_pii_and_enable_human_outcome_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _completed_benchmark(tmp_path, monkeypatch)
    exported = export_blind_tasks(root, tmp_path / "review-tasks.json")
    payload = json.loads(exported.read_text())
    private = json.loads((root / "human" / "private-map.json").read_text())["items"]
    serialized = exported.read_text()
    assert "Alice Example" not in serialized
    assert "alice@example.com" not in serialized

    tasks = {task["blind_item_id"]: task for task in payload["tasks"]}
    selected = [
        private["cv_claims:baseline"]["blind_item_id"],
        private["cv_claims:final"]["blind_item_id"],
        private["baseline_final"]["blind_item_id"],
    ]
    for blind_id in selected:
        task = tasks[blind_id]
        for rater in ("rater-a", "rater-b"):
            label: dict[str, Any] = {
                "schema_version": 2,
                "benchmark_id": payload["benchmark_id"],
                "blind_item_id": blind_id,
                "rater_id": rater,
                "created_at": "2026-07-15T00:00:00Z",
            }
            if task["kind"] == "baseline_final_pair":
                label["pairwise_preference"] = private["baseline_final"][
                    "preferred_revision_side"
                ]
            else:
                values = {claim["claim_id"]: "supported" for claim in task["claims"]}
                if private["cv_claims:baseline"]["blind_item_id"] == blind_id:
                    values[next(iter(values))] = "unsupported"
                label["claim_support"] = values
            source = tmp_path / f"{blind_id}-{rater}.json"
            source.write_text(json.dumps(label))
            import_label(source)

    report = build_report(root)
    assert report["real_cv_improvement"]["status"] == "available"
    assert report["real_cv_improvement"]["human_pipeline_preference_rate"] == 1.0
    assert report["hallucination_reduction"]["status"] == "available"
    assert report["hallucination_reduction"]["unsupported_rate_reduction"] > 0


def test_label_import_rejects_unknown_task_and_v1_capture_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = _completed_benchmark(tmp_path, monkeypatch)
    export_blind_tasks(root, tmp_path / "tasks.json")
    bad = {
        "schema_version": 2,
        "benchmark_id": json.loads((root / "manifest.json").read_text())["benchmark_id"],
        "blind_item_id": "task-does-not-exist",
        "rater_id": "rater-a",
        "pairwise_preference": "a",
        "created_at": "now",
    }
    path = tmp_path / "bad-label.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="unknown blind task"):
        import_label(path)

    request = tmp_path / "celestial" / "captures" / "capture-v2" / "request.json"
    value = json.loads(request.read_text())
    value["schema_version"] = 1
    request.chmod(0o600)
    request.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="v1"):
        update_request("capture-v2", status="ready")


def test_codex_is_read_only_toolless_and_unversioned_models_are_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        observed.extend(command)
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text("{}")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("the_celestial.provider.subprocess.run", fake_run)
    assert run_prompt("codex", "gpt-5.4", "content") == "{}"
    assert observed.count("--disable") == 2
    assert "shell_tool" in observed and "unified_exec" in observed
    assert "--ignore-user-config" in observed and "--ignore-rules" in observed
    assert observed[observed.index("--sandbox") + 1] == "read-only"
    with pytest.raises(ValueError, match="versioned"):
        run_prompt("claude", "sonnet", "content")
    with pytest.raises(ProviderCapabilityError, match="blocked"):
        run_prompt("agy", "gemini", "content")


def test_launcher_tmpfs_home_is_owned_by_the_non_root_celestial_user() -> None:
    launcher = (Path(__file__).resolve().parents[1] / "start.sh").read_text(encoding="utf-8")
    assert (
        "--tmpfs /home/celestial:rw,nosuid,nodev,size=32m,mode=0700,uid=1000,gid=1000"
        in launcher
    )
