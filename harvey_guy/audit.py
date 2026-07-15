from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .io import utc_now


class BoundaryAuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    timestamp: str = Field(min_length=1)
    script: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    transition: str = Field(min_length=1)
    session_id: str | None
    exit_code: int = Field(ge=0)
    status: Literal["PASS", "FAIL"]
    details: str | None


def append_boundary_event(
    run_dir: Path,
    *,
    script: str,
    mode: str,
    transition: str,
    session_id: str | None,
    exit_code: int,
    details: str | None,
) -> Path:
    run_dir = run_dir.resolve()
    if not (run_dir / "state.json").is_file():
        raise ValueError(f"Run directory has no state.json: {run_dir}")
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    audit_path = logs_dir / "boundary_audit.jsonl"
    event = BoundaryAuditEvent(
        timestamp=utc_now(),
        script=script,
        mode=mode,
        transition=transition,
        session_id=session_id or None,
        exit_code=exit_code,
        status="PASS" if exit_code == 0 else "FAIL",
        details=details or None,
    )
    line = json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n"
    lock_path = logs_dir / ".boundary_audit.lock"
    with lock_path.open("a+") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        with audit_path.open("a", encoding="utf-8") as audit_handle:
            audit_handle.write(line)
            audit_handle.flush()
            os.fsync(audit_handle.fileno())
        directory_fd = os.open(logs_dir, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    return audit_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append one durable boundary audit event")
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--script", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--transition", required=True)
    parser.add_argument("--session-id")
    parser.add_argument("--exit-code", required=True, type=int)
    parser.add_argument("--details")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        append_boundary_event(
            args.run_dir,
            script=args.script,
            mode=args.mode,
            transition=args.transition,
            session_id=args.session_id,
            exit_code=args.exit_code,
            details=args.details,
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Boundary audit failed: {exc}") from exc


if __name__ == "__main__":
    main()
