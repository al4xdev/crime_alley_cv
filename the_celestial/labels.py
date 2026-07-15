from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .capture import data_root
from .io import atomic_write_json, digest_text, read_json_object
from .models import ConversationEnvelope, HumanLabel


def export_blind_tasks(benchmark_root: Path, output: Path) -> Path:
    manifest = read_json_object(benchmark_root / "manifest.json")
    case_root = data_root() / "cases" / str(manifest["case_id"])
    tasks: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    for path in sorted((case_root / "envelopes").glob("*/*.json")):
        envelope = ConversationEnvelope.model_validate_json(json.dumps(read_json_object(path)))
        if envelope.status.value != "observed":
            continue
        if envelope.role.value in seen_roles and envelope.role.value != "bill":
            continue
        seen_roles.add(envelope.role.value)
        item_id = f"{envelope.role.value}-{envelope.invocation:03d}"
        tasks.append(
            {
                "blind_item_id": item_id,
                "role": envelope.role.value,
                "messages": [message.model_dump(mode="json") for message in envelope.messages],
            }
        )
    for path in sorted((case_root / "envelopes" / "bill").glob("*.json")):
        envelope = ConversationEnvelope.model_validate_json(json.dumps(read_json_object(path)))
        messages = {message.source_label: message.content for message in envelope.messages}
        if "cv_before" in messages and "cv_after" in messages:
            tasks.append(
                {
                    "blind_item_id": "pair-" + digest_text(path.name)[:12],
                    "kind": "cv_pair",
                    "candidate_a": messages["cv_before"],
                    "candidate_b": messages["cv_after"],
                }
            )
    baseline_path = case_root / "baseline.md"
    bill_paths = sorted((case_root / "envelopes" / "bill").glob("*.json"))
    if baseline_path.is_file() and bill_paths:
        final_bill = ConversationEnvelope.model_validate_json(bill_paths[-1].read_text())
        final_outputs = {
            message.source_label: message.content
            for message in final_bill.messages
            if message.kind == "output"
        }
        if "cv_after" in final_outputs:
            tasks.append(
                {
                    "blind_item_id": "pair-baseline-final",
                    "kind": "cv_pair",
                    "candidate_a": baseline_path.read_text(encoding="utf-8"),
                    "candidate_b": final_outputs["cv_after"],
                }
            )
    payload = {
        "schema_version": 1,
        "benchmark_id": manifest["benchmark_id"],
        "instructions": (
            "Score content only. Provider, model and run identity are intentionally hidden."
        ),
        "tasks": tasks,
    }
    atomic_write_json(output, payload)
    return output


def import_label(path: Path) -> Path:
    label = HumanLabel.model_validate(read_json_object(path))
    root = data_root() / "labels" / label.benchmark_id
    destination = root / f"{label.blind_item_id}-{label.rater_id}.json"
    atomic_write_json(destination, label.model_dump(mode="json"), exclusive=True)
    return destination
