from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .io import atomic_write_json, atomic_write_text, digest_json, digest_text, read_json_object
from .models import (
    AgentRole,
    ContentMessage,
    ConversationEnvelope,
    Coverage,
    EnvelopeStatus,
    EvidenceEntry,
    FrozenCaseManifest,
)

CAPTURE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
TEXT_EXTENSIONS = {
    ".c",
    ".cc",
    ".cfg",
    ".conf",
    ".cpp",
    ".css",
    ".csv",
    ".fish",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".rb",
    ".rs",
    ".rst",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
MAX_FILE_BYTES = 256 * 1024
MAX_REPOSITORY_BYTES = 5 * 1024 * 1024
MAX_CASE_BYTES = 25 * 1024 * 1024
MAX_FILES_EXAMINED = 10_000


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def data_root() -> Path:
    configured = os.environ.get("CELESTIAL_DATA_DIR")
    root = (
        Path(configured).resolve()
        if configured
        else (Path(__file__).parent.parent / ".celestial").resolve()
    )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    return root


def capture_root(capture_id: str) -> Path:
    if CAPTURE_ID.fullmatch(capture_id) is None:
        raise ValueError(f"Invalid Celestial capture ID: {capture_id!r}")
    return data_root() / "captures" / capture_id


def _secure(path: Path) -> None:
    current = path if path.is_dir() else path.parent
    while current != data_root().parent and current.is_relative_to(data_root()):
        current.chmod(0o700)
        if current == data_root():
            break
        current = current.parent
    if path.is_file():
        path.chmod(0o600)


def _message(message_id: str, kind: str, label: str, content: str) -> ContentMessage:
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
    baseline_provider: str | None = None,
    baseline_model: str | None = None,
) -> Path:
    root = capture_root(capture_id)
    request = {
        "schema_version": 3,
        "capture_id": capture_id,
        "run_id": run_id,
        "run_dir": run_dir,
        "subject_provider": subject_provider,
        "subject_model": subject_model,
        "baseline_provider": baseline_provider,
        "baseline_model": baseline_model,
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
            "schema_version",
            "capture_id",
            "run_id",
            "subject_provider",
            "subject_model",
            "baseline_provider",
            "baseline_model",
            "celestial_requested",
            "judge_provider",
            "judge_model",
        )
        if any(existing.get(key) != request.get(key) for key in immutable):
            raise ValueError("Celestial capture request conflicts with an existing request")
        return path
    atomic_write_json(path, request, exclusive=True)
    _secure(path)
    return path


def update_request(capture_id: str, **updates: Any) -> Path:
    path = capture_root(capture_id) / "request.json"
    value = read_json_object(path)
    if value.get("schema_version") not in {2, 3}:
        raise ValueError("Celestial v1 captures are audit-only; create a new capture")
    value.update(updates)
    value["updated_at"] = utc_now()
    atomic_write_json(path, value)
    _secure(path)
    return path


def record_case_input(capture_id: str, label: str, content: str) -> Path:
    if re.fullmatch(r"[a-z][a-z0-9_]{0,79}", label) is None:
        raise ValueError("Invalid case input label")
    path = capture_root(capture_id) / "inputs" / f"{label}.md"
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise ValueError(f"Celestial case input is immutable: {label}")
        return path
    atomic_write_text(path, content, exclusive=True)
    _secure(path)
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
    fingerprint = digest_json({"instruction": instruction, "inputs": sorted(inputs.items())})
    path = capture_root(capture_id) / "envelopes" / parsed_role.value / f"{invocation:03d}.json"
    stable = {
        "schema_version": 2,
        "capture_id": capture_id,
        "run_id": run_id,
        "case_key": fingerprint[:20],
        "role": parsed_role.value,
        "invocation": invocation,
        "coverage": coverage.value,
        "status": status.value,
        "input_fingerprint": fingerprint,
        "messages": [message.model_dump(mode="json") for message in messages],
    }
    if path.exists():
        existing = read_json_object(path)
        if {key: existing.get(key) for key in stable} != stable:
            raise ValueError(f"Celestial envelope is immutable: {path}")
        return path
    payload = {**stable, "created_at": utc_now()}
    ConversationEnvelope.model_validate_json(json.dumps(payload))
    atomic_write_json(path, payload, exclusive=True)
    _secure(path)
    return path


def read_text_if_file(path: Path) -> str | None:
    if not path.is_file() or path.is_symlink():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _snapshot_evidence(
    roots: list[Path], destination: Path
) -> tuple[list[EvidenceEntry], list[str]]:
    entries: list[EvidenceEntry] = []
    omissions: list[str] = []
    case_bytes = 0
    examined = 0
    for repository_index, root in enumerate(sorted(roots), 1):
        if not root.is_dir() or root.is_symlink():
            continue
        repository = re.sub(r"[^a-z0-9._-]+", "-", root.name.casefold()).strip("-")
        repository = repository or f"repository-{repository_index}"
        repository_bytes = 0
        for source in sorted(root.rglob("*")):
            examined += 1
            if examined > MAX_FILES_EXAMINED:
                omissions.append("case:file_count_limit")
                return entries, omissions
            if source.is_symlink() or not source.is_file() or ".git" in source.parts:
                continue
            relative = source.relative_to(root)
            if source.suffix.casefold() not in TEXT_EXTENSIONS:
                omissions.append(f"{repository}/{relative}:non_text_extension")
                continue
            raw = source.read_bytes()
            if b"\0" in raw[:8192]:
                omissions.append(f"{repository}/{relative}:binary")
                continue
            truncated = len(raw) > MAX_FILE_BYTES
            content = raw[:MAX_FILE_BYTES]
            if repository_bytes + len(content) > MAX_REPOSITORY_BYTES:
                omissions.append(f"{repository}:repository_size_limit")
                break
            if case_bytes + len(content) > MAX_CASE_BYTES:
                omissions.append("case:case_size_limit")
                return entries, omissions
            target = destination / repository / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(0o600)
            repository_bytes += len(content)
            case_bytes += len(content)
            source_id = f"repo/{repository}/{str(relative).replace(os.sep, '/').casefold()}"
            entries.append(
                EvidenceEntry(
                    source_id=source_id,
                    repository=repository,
                    relative_path=str(relative),
                    sha256=digest_text(content.decode("utf-8", errors="replace")),
                    size=len(content),
                    truncated=truncated,
                )
            )
            if truncated:
                omissions.append(f"{repository}/{relative}:file_truncated")
    return entries, omissions


def _file_map(root: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            values[str(path.relative_to(root))] = digest_text(
                path.read_bytes().decode("utf-8", errors="replace")
            )
    return values


def freeze_capture(capture_id: str, *, evidence_roots: list[Path] | None = None) -> Path:
    root = capture_root(capture_id)
    request = read_json_object(root / "request.json")
    if request.get("schema_version") not in {2, 3}:
        raise ValueError("Celestial v1 captures are audit-only")
    if request.get("status") not in {"capture_complete", "frozen", "ready", "captured_disabled"}:
        raise ValueError("Capture must be complete and error-free before freezing")
    if request.get("last_capture_error"):
        raise ValueError("Capture contains errors and cannot be frozen")
    required_inputs = {"initial_cv.md", "job_description.md", "final_cv.md"}
    present_inputs = {path.name for path in (root / "inputs").glob("*.md")}
    if not required_inputs <= present_inputs:
        missing = sorted(required_inputs - present_inputs)
        raise ValueError(f"Capture is missing required case inputs: {missing}")
    envelopes = sorted((root / "envelopes").glob("*/*.json"))
    if not envelopes:
        raise ValueError("Cannot freeze a capture with no envelopes")
    staging_parent = data_root() / "cases" / ".staging"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="case-", dir=staging_parent))
    try:
        for source in envelopes:
            value = read_json_object(source)
            ConversationEnvelope.model_validate_json(json.dumps(value))
            target = staging / "envelopes" / source.relative_to(root / "envelopes")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        for source in sorted((root / "inputs").glob("*.md")):
            target = staging / "inputs" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        entries, omissions = _snapshot_evidence(evidence_roots or [], staging / "evidence")
        files = _file_map(staging)
        content_digest = digest_json(files)
        case_id = content_digest[:24]
        case_root = data_root() / "cases" / case_id
        manifest = FrozenCaseManifest(
            case_id=case_id,
            capture_id=capture_id,
            run_id=str(request["run_id"]),
            subject_provider=request["subject_provider"],
            subject_model=request.get("subject_model"),
            envelope_count=len(envelopes),
            evidence_entries=entries,
            omissions=omissions,
            files=files,
            content_digest=content_digest,
            created_at=utc_now(),
        )
        atomic_write_json(staging / "manifest.json", manifest.model_dump(mode="json"))
        if case_root.exists():
            verify_frozen_case(case_id)
            shutil.rmtree(staging)
        else:
            staging.rename(case_root)
            for directory in [case_root, *[p for p in case_root.rglob("*") if p.is_dir()]]:
                directory.chmod(0o500)
            for file_path in [p for p in case_root.rglob("*") if p.is_file()]:
                file_path.chmod(0o400)
        update_request(capture_id, status="frozen", case_id=case_id, case_digest=content_digest)
        return case_root
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def verify_frozen_case(case_id: str) -> dict[str, Any]:
    if re.fullmatch(r"[0-9a-f]{24}", case_id) is None:
        raise ValueError("Invalid case ID")
    root = data_root() / "cases" / case_id
    manifest = FrozenCaseManifest.model_validate_json((root / "manifest.json").read_text())
    if manifest.case_id != case_id or _file_map(root) != manifest.files:
        raise ValueError("Frozen case file map mismatch")
    if digest_json(manifest.files) != manifest.content_digest:
        raise ValueError("Frozen case digest mismatch")
    return {
        "case_id": case_id,
        "envelope_count": manifest.envelope_count,
        "evidence_entries": len(manifest.evidence_entries),
        "digest": manifest.content_digest,
    }
