from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .io import atomic_write_json, digest_json, digest_text, read_json_object
from .models import (
    AgentRole,
    ContentMessage,
    ConversationEnvelope,
    Coverage,
    EnvelopeStatus,
)

CAPTURE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def data_root() -> Path:
    configured = os.environ.get("CELESTIAL_DATA_DIR")
    if configured:
        return Path(configured).resolve()
    return (Path(__file__).resolve().parent.parent / ".celestial").resolve()


def capture_root(capture_id: str) -> Path:
    if CAPTURE_ID.fullmatch(capture_id) is None:
        raise ValueError(f"Invalid Celestial capture ID: {capture_id!r}")
    return data_root() / "captures" / capture_id


def _message(
    message_id: str,
    kind: str,
    label: str,
    content: str,
) -> ContentMessage:
    return ContentMessage(
        message_id=message_id,
        kind=kind,  # type: ignore[arg-type]
        source_label=label,
        content=content,
        sha256=digest_text(content),
    )


def create_run_request(
    *,
    capture_id: str,
    run_id: str,
    run_dir: str,
    subject_provider: str,
    subject_model: str | None,
    celestial_requested: bool,
    judge_provider: str | None,
    judge_model: str | None,
) -> Path:
    root = capture_root(capture_id)
    request = {
        "schema_version": 1,
        "capture_id": capture_id,
        "run_id": run_id,
        "run_dir": run_dir,
        "subject_provider": subject_provider,
        "subject_model": subject_model,
        "celestial_requested": celestial_requested,
        "judge_provider": judge_provider,
        "judge_model": judge_model,
        "status": "capturing",
        "created_at": utc_now(),
    }
    path = root / "request.json"
    if path.exists():
        existing = read_json_object(path)
        immutable = (
            "capture_id",
            "run_id",
            "subject_provider",
            "subject_model",
            "celestial_requested",
            "judge_provider",
            "judge_model",
        )
        if any(existing.get(key) != request.get(key) for key in immutable):
            raise ValueError("Celestial capture request conflicts with an existing request")
        return path
    atomic_write_json(path, request, exclusive=True)
    return path


def update_request(capture_id: str, **updates: Any) -> Path:
    path = capture_root(capture_id) / "request.json"
    value = read_json_object(path)
    value.update(updates)
    value["updated_at"] = utc_now()
    atomic_write_json(path, value)
    return path


def record_envelope(
    *,
    capture_id: str,
    run_id: str,
    role: AgentRole | str,
    invocation: int,
    instruction: tuple[str, str] | None,
    inputs: dict[str, str],
    outputs: dict[str, str],
    status: EnvelopeStatus = EnvelopeStatus.OBSERVED,
    coverage: Coverage = Coverage.PROMPT_OUTPUT_ONLY,
) -> Path:
    parsed_role = AgentRole(role)
    messages: list[ContentMessage] = []
    if instruction is not None:
        label, content = instruction
        messages.append(_message("instruction", "instruction", label, content))
    for index, (label, content) in enumerate(sorted(inputs.items()), 1):
        messages.append(_message(f"input-{index}", "input", label, content))
    for index, (label, content) in enumerate(sorted(outputs.items()), 1):
        messages.append(_message(f"output-{index}", "output", label, content))
    input_fingerprint = digest_json({"instruction": instruction, "inputs": sorted(inputs.items())})
    case_id = input_fingerprint[:20]
    envelope = ConversationEnvelope(
        capture_id=capture_id,
        run_id=run_id,
        case_id=case_id,
        role=parsed_role,
        invocation=invocation,
        coverage=coverage,
        status=status,
        input_fingerprint=input_fingerprint,
        messages=messages,
        created_at=utc_now(),
    )
    path = capture_root(capture_id) / "envelopes" / parsed_role.value / f"{invocation:03d}.json"
    payload = envelope.model_dump(mode="json")
    if path.exists():
        if read_json_object(path) != payload:
            raise ValueError(f"Celestial envelope is immutable: {path}")
        return path
    atomic_write_json(path, payload, exclusive=True)
    return path


def read_text_if_file(path: Path) -> str | None:
    if not path.is_file() or path.is_symlink():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def freeze_capture(capture_id: str) -> Path:
    root = capture_root(capture_id)
    request = read_json_object(root / "request.json")
    envelopes = sorted((root / "envelopes").glob("*/*.json"))
    if not envelopes:
        raise ValueError("Cannot freeze a capture with no envelopes")
    envelope_values = [read_json_object(path) for path in envelopes]
    case_id = digest_json(envelope_values)[:24]
    case_root = data_root() / "cases" / case_id
    if case_root.exists():
        manifest = read_json_object(case_root / "manifest.json")
        if manifest.get("capture_digest") != digest_json(envelope_values):
            raise ValueError("Frozen case ID collision")
        return case_root
    case_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{case_root.name}.staging-", dir=case_root.parent))
    (staging / "envelopes").mkdir(parents=True)
    for source in envelopes:
        relative = source.relative_to(root / "envelopes")
        destination = staging / "envelopes" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    manifest = {
        "schema_version": 1,
        "case_id": case_id,
        "capture_id": capture_id,
        "run_id": request["run_id"],
        "capture_digest": digest_json(envelope_values),
        "envelope_count": len(envelopes),
        "created_at": utc_now(),
    }
    atomic_write_json(staging / "manifest.json", manifest)
    staging.rename(case_root)
    update_request(capture_id, status="frozen", case_id=case_id)
    return case_root


def verify_frozen_case(case_id: str) -> dict[str, Any]:
    root = data_root() / "cases" / case_id
    manifest = read_json_object(root / "manifest.json")
    values = [read_json_object(path) for path in sorted((root / "envelopes").glob("*/*.json"))]
    for value in values:
        ConversationEnvelope.model_validate_json(json.dumps(value))
    actual = digest_json(values)
    if actual != manifest.get("capture_digest"):
        raise ValueError("Frozen case digest mismatch")
    return {"case_id": case_id, "envelope_count": len(values), "digest": actual}
