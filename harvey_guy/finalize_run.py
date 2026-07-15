from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harvey_guy.io import atomic_copy, atomic_write_text
from harvey_guy.layout import SessionLayout, validate_session_id


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    timestamp: str
    source: str
    action: str
    status: str
    session_id: str | None
    details: str | None


@dataclass(frozen=True, slots=True)
class RunContext:
    run_dir: Path
    session_root: Path
    current_session_id: str | None
    current_session_dir: Path | None


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    values: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.is_file():
        return values, [f"Missing journal: {path}"]
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value: Any = json.loads(line)
            if not isinstance(value, dict):
                raise TypeError("entry is not a JSON object")
            values.append(value)
        except (TypeError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}, line {line_number}: {exc}")
    return values, errors


def _load_context(state_path: Path) -> RunContext:
    state = _load_json_object(state_path)
    try:
        run_dir = Path(str(state["run_dir"])).resolve()
        session_root = Path(str(state["session_root"])).resolve()
        current_id_value = state.get("current_session_id")
        current_dir_value = state.get("current_session_dir")
        current_id = str(current_id_value) if current_id_value is not None else None
        current_dir = Path(str(current_dir_value)).resolve() if current_dir_value else None
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid run state {state_path}: {exc}") from exc
    if run_dir != state_path.resolve().parent:
        raise ValueError("state.json run_dir does not match its containing directory")
    return RunContext(run_dir, session_root, current_id, current_dir)


def _pipeline_timeline(values: list[dict[str, Any]]) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    for value in values:
        detail_value = value.get("details")
        details = (
            json.dumps(detail_value, ensure_ascii=False, sort_keys=True)
            if detail_value
            else None
        )
        events.append(
            TimelineEvent(
                timestamp=str(value.get("timestamp", "unknown")),
                source="control-plane",
                action=str(value.get("event") or value.get("operation") or "unknown"),
                status="PASS",
                session_id=(
                    str(value["session_id"]) if value.get("session_id") is not None else None
                ),
                details=details,
            )
        )
    return events


def _boundary_timeline(values: list[dict[str, Any]]) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    for value in values:
        mode = str(value.get("mode", "unknown"))
        transition = value.get("transition")
        suffix = f" ({transition})" if transition else ""
        events.append(
            TimelineEvent(
                timestamp=str(value.get("timestamp", "unknown")),
                source="boundary",
                action=f"{value.get('script', 'unknown')} {mode}{suffix}",
                status=str(value.get("status", "UNKNOWN")),
                session_id=(
                    str(value["session_id"]) if value.get("session_id") is not None else None
                ),
                details=str(value["details"]) if value.get("details") else None,
            )
        )
    return events


def _session_locations(
    context: RunContext,
    pipeline_events: list[dict[str, Any]],
) -> dict[str, Path]:
    locations: dict[str, Path] = {}
    for event in pipeline_events:
        raw_id = event.get("session_id")
        details = event.get("details")
        raw_dir = details.get("session_dir") if isinstance(details, dict) else None
        if raw_id is None or raw_dir is None:
            continue
        session_id = validate_session_id(str(raw_id))
        locations[session_id] = Path(str(raw_dir)).resolve()
    if context.current_session_id and context.current_session_dir:
        locations[validate_session_id(context.current_session_id)] = context.current_session_dir

    for session_id, directory in locations.items():
        expected = context.session_root / f"karen_guard_{session_id}"
        if directory != expected.resolve():
            raise ValueError(f"Session {session_id} is outside the configured session root")
    return locations


def _archive_sessions(run_dir: Path, locations: dict[str, Path]) -> dict[str, list[Path]]:
    archived: dict[str, list[Path]] = {}
    for session_id, session_dir in locations.items():
        layout = SessionLayout(session_dir)
        files: list[Path] = []
        for category, source_root in (
            ("artifacts", layout.artifacts),
            ("contracts", layout.contracts),
            ("logs", layout.logs),
        ):
            if not source_root.is_dir():
                continue
            for source in sorted(source_root.rglob("*")):
                if source.is_symlink() or not source.is_file():
                    continue
                destination = (
                    run_dir / "sessions" / session_id / category / source.relative_to(source_root)
                )
                atomic_copy(source, destination)
                files.append(destination)
        archived[session_id] = files
    return archived


def _write_pipeline_log(
    run_dir: Path,
    events_path: Path,
    audit_path: Path,
    archived: dict[str, list[Path]],
) -> Path:
    sources = [events_path, audit_path]
    sources.extend(
        path
        for paths in archived.values()
        for path in paths
        if path.parent.name == "logs" or "logs" in path.relative_to(run_dir).parts
    )
    output = run_dir / "logs" / "pipeline.log"
    chunks: list[str] = []
    for source in sources:
        if not source.is_file() or source == output:
            continue
        relative = source.relative_to(run_dir) if source.is_relative_to(run_dir) else source
        content = source.read_text(encoding="utf-8", errors="replace")
        chunks.append(f"===== {relative} =====\n{content.rstrip()}\n")
    atomic_write_text(output, "\n".join(chunks))
    return output


def _inventory(run_dir: Path) -> list[Path]:
    return [
        path
        for path in sorted(run_dir.rglob("*"))
        if path.is_file()
        and path.name != "log_tree.md"
        and not path.name.endswith(".lock")
        and "transactions" not in path.parts
    ]


def _write_tree(
    run_dir: Path,
    timeline: list[TimelineEvent],
    parse_errors: list[str],
    archived: dict[str, list[Path]],
    pipeline_log: Path,
) -> Path:
    output = run_dir / "log_tree.md"
    failures = sum(event.status == "FAIL" for event in timeline)
    warnings = sum(event.status == "WARNING" for event in timeline) + len(parse_errors)
    lines = [
        "# Pipeline log tree",
        "",
        f"- Timeline events: {len(timeline)}",
        f"- Sessions archived: {len(archived)}",
        f"- Failures: {failures}",
        f"- Warnings: {warnings}",
        f"- Consolidated raw log: `{pipeline_log.relative_to(run_dir)}`",
        "",
        "## Chronological trace",
        "",
    ]
    for index, event in enumerate(timeline, 1):
        session = f" session=`{event.session_id}`" if event.session_id else ""
        details = f" — {event.details}" if event.details else ""
        lines.append(
            f"{index}. `{event.timestamp}` [{event.status}] `{event.source}` "
            f"{event.action}{session}{details}"
        )

    lines.extend(["", "## Durable artifact tree", ""])
    for path in _inventory(run_dir):
        lines.append(f"- `{path.relative_to(run_dir)}` ({path.stat().st_size} bytes)")

    if parse_errors:
        lines.extend(["", "## Journal parse warnings", ""])
        lines.extend(f"- {error}" for error in parse_errors)
    lines.append("")
    atomic_write_text(output, "\n".join(lines))
    return output


def finalize_run(state_path: Path) -> Path:
    state_path = state_path.resolve()
    context = _load_context(state_path)
    events_path = context.run_dir / "events.jsonl"
    audit_path = context.run_dir / "logs" / "boundary_audit.jsonl"
    pipeline_values, pipeline_errors = _load_jsonl(events_path)
    boundary_values, boundary_errors = _load_jsonl(audit_path)
    locations = _session_locations(context, pipeline_values)
    archived = _archive_sessions(context.run_dir, locations)
    pipeline_log = _write_pipeline_log(context.run_dir, events_path, audit_path, archived)
    timeline = _pipeline_timeline(pipeline_values) + _boundary_timeline(boundary_values)
    timeline.sort(key=lambda event: (event.timestamp, event.source, event.action))
    return _write_tree(
        context.run_dir,
        timeline,
        pipeline_errors + boundary_errors,
        archived,
        pipeline_log,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consolidate one pipeline run's audit trail")
    parser.add_argument("--state", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        output = finalize_run(args.state)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Cannot finalize run: {exc}") from exc
    print(output)


if __name__ == "__main__":
    main()
