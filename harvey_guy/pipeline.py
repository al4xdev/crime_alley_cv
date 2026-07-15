from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from the_celestial.capture import (
    capture_root,
    create_run_request,
    freeze_capture,
    read_text_if_file,
    record_case_input,
    record_envelope,
    update_request,
)
from the_celestial.io import read_json_object as read_celestial_json
from the_celestial.models import AgentRole, Coverage, EnvelopeStatus

from .evaluation import read_evaluation
from .harvey_guy import Harvey
from .io import (
    atomic_copy,
    atomic_write_json,
    atomic_write_text,
    utc_now,
)
from .layout import SessionLayout
from .render_instructions import render_agent

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
JOB_HEADER = re.compile(r"^# .+ — .+$")
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


class PipelineError(RuntimeError):
    pass


class Phase(StrEnum):
    READY = "ready"
    SHADOW_RUNNING = "shadow_running"
    KAREN_READY = "karen_ready"
    NEEDS_REVISION = "needs_revision"
    BILL_RUNNING = "bill_running"
    COACHING_READY = "coaching_ready"
    DONNA_RUNNING = "donna_running"
    COMPLETE = "complete"


TRANSITION_PHASES: dict[str, tuple[set[Phase], set[Phase]]] = {
    "start_session": ({Phase.READY}, {Phase.SHADOW_RUNNING}),
    "mark_shadow_ready": ({Phase.SHADOW_RUNNING}, {Phase.KAREN_READY}),
    "record_evaluation": (
        {Phase.KAREN_READY},
        {Phase.NEEDS_REVISION, Phase.COACHING_READY},
    ),
    "prepare_bill": ({Phase.NEEDS_REVISION}, {Phase.BILL_RUNNING}),
    "commit_bill": ({Phase.BILL_RUNNING}, {Phase.READY}),
    "prepare_donna": ({Phase.COACHING_READY}, {Phase.DONNA_RUNNING}),
    "complete_donna": ({Phase.DONNA_RUNNING}, {Phase.COMPLETE}),
}


class Outcome(StrEnum):
    SUCCESS = "success"
    MAX_ITERATIONS = "max_iterations"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class GuardReference(StrictModel):
    schema_version: Literal[1] = 1
    kind: Literal["bill", "donna"]
    path: str
    sha256: str = Field(pattern=SHA256_HEX.pattern)
    revision: int = Field(ge=1)


class BillGuard(StrictModel):
    schema_version: Literal[2] = 2
    run_id: str
    revision: int = Field(ge=1)
    iteration: int = Field(ge=1)
    cv_sha256: str = Field(pattern=SHA256_HEX.pattern)
    protected: dict[str, dict[str, dict[str, str]]]
    host_repository: dict[str, dict[str, str]]


class DonnaGuard(StrictModel):
    schema_version: Literal[3] = 3
    run_id: str
    revision: int = Field(ge=1)
    action_plan_before: dict[str, dict[str, str]]
    protected: dict[str, dict[str, dict[str, str]]]
    host_repository: dict[str, dict[str, str]]


class PendingWrite(StrictModel):
    source: str
    target: str
    size: int = Field(ge=0)
    sha256: str = Field(pattern=SHA256_HEX.pattern)


class PendingManifest(StrictModel):
    schema_version: Literal[2] = 2
    operation: Literal[
        "start_session",
        "mark_shadow_ready",
        "record_evaluation",
        "prepare_bill",
        "commit_bill",
        "prepare_donna",
        "complete_donna",
    ]
    revision: int = Field(ge=1)
    writes: list[PendingWrite] = Field(min_length=1)


class RunState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[3] = 3
    revision: int = Field(default=0, ge=0)
    run_id: str
    run_dir: str
    data_dir: str
    session_root: str
    agent_provider: Literal["agy", "claude", "codex", "replay"] = "agy"
    agent_model: str | None = None
    celestial_capture_id: str | None = None
    celestial_requested: bool = False
    celestial_judge_provider: Literal["agy", "claude", "codex"] | None = None
    celestial_judge_model: str | None = None
    max_iterations: int = Field(ge=1)
    min_fit_score: int = Field(ge=0, le=100)
    karen_reads_background: bool
    phase: Phase = Phase.READY
    outcome: Outcome | None = None
    iterations_completed: int = Field(default=0, ge=0)
    latest_score: int | None = Field(default=None, ge=0, le=100)
    current_session_id: str | None = None
    current_session_dir: str | None = None
    bill_guard: GuardReference | None = None
    donna_guard: GuardReference | None = None
    created_at: str
    updated_at: str

    @model_validator(mode="after")
    def validate_celestial_configuration(self) -> RunState:
        judge_values = (self.celestial_judge_provider, self.celestial_judge_model)
        if any(judge_values) and not all(judge_values):
            raise ValueError("Celestial judge provider and model must be configured together")
        if self.celestial_requested and (
            self.celestial_capture_id is None or self.agent_model is None or not all(judge_values)
        ):
            raise ValueError(
                "An enabled Celestial benchmark requires capture, subject model and judge model"
            )
        if self.celestial_requested and (
            self.agent_provider not in {"claude", "codex"}
            or self.celestial_judge_provider not in {"claude", "codex"}
        ):
            raise ValueError("Celestial calls fail closed to Claude or Codex providers")
        return self

    @property
    def run_path(self) -> Path:
        return Path(self.run_dir)

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)

    @property
    def session_path(self) -> Path:
        if self.current_session_dir is None:
            raise PipelineError("Run has no active session")
        return Path(self.current_session_dir)


@dataclass(frozen=True)
class PlannedWrite:
    source: Path
    target: Path
    size: int
    sha256: str


def _parse_run_state(raw: str) -> RunState:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Run state must be a JSON object")
    if value.get("schema_version") == 2:
        value = {
            **value,
            "schema_version": 3,
            "agent_model": None,
            "celestial_capture_id": None,
            "celestial_requested": False,
            "celestial_judge_provider": None,
            "celestial_judge_model": None,
        }
    return RunState.model_validate_json(json.dumps(value))


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def _text_sha256(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def _ensure_no_symlink_components(path: Path, *, include_leaf: bool = True) -> None:
    candidates = list(reversed(path.parents))
    if include_leaf:
        candidates.append(path)
    for candidate in candidates:
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise PipelineError(f"Symlink path component is not allowed: {candidate}")


def _ensure_regular_file(path: Path, label: str) -> None:
    _ensure_no_symlink_components(path)
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise PipelineError(f"Cannot inspect {label}: {path}: {exc}") from exc
    if not stat.S_ISREG(mode):
        raise PipelineError(f"{label} must be a regular file: {path}")


class TransitionTransaction:
    """Stage every durable write before publishing a recoverable intent."""

    def __init__(self, run_dir: Path, operation: str, revision: int) -> None:
        transactions_dir = run_dir / "transactions"
        transactions_dir.mkdir(parents=True, exist_ok=True)
        self.directory = Path(
            tempfile.mkdtemp(prefix=f"{revision:06d}-{operation}-", dir=transactions_dir)
        )
        self.operation = operation
        self.revision = revision
        self.writes: list[PlannedWrite] = []

    def _payload_path(self) -> Path:
        return self.directory / f"payload-{len(self.writes):04d}"

    def _append(self, payload: Path, target: Path) -> None:
        self.writes.append(
            PlannedWrite(
                source=payload,
                target=target.absolute(),
                size=payload.stat().st_size,
                sha256=_file_sha256(payload),
            )
        )

    def copy(self, source: Path, target: Path) -> None:
        payload = self._payload_path()
        atomic_copy(source, payload)
        self._append(payload, target)

    def write_text(self, target: Path, content: str) -> None:
        payload = self._payload_path()
        atomic_write_text(payload, content)
        self._append(payload, target)

    def write_json(self, target: Path, value: dict[str, Any]) -> None:
        self.write_text(target, _json_text(value))


Transition = Callable[[RunState, TransitionTransaction], tuple[str, dict[str, Any]]]


class RunStore:
    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path.resolve()
        self.run_dir = self.state_path.parent
        self.events_path = self.run_dir / "events.jsonl"
        self.lock_path = self.run_dir / ".state.lock"
        self.pending_path = self.run_dir / "transactions" / "pending.json"

    @contextmanager
    def _lock(self) -> Iterator[None]:
        with self.lock_path.open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _load(self) -> RunState:
        try:
            return _parse_run_state(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, ValidationError) as exc:
            raise PipelineError(f"Cannot load run state {self.state_path}: {exc}") from exc

    def _events(self) -> list[dict[str, Any]]:
        try:
            lines = self.events_path.read_text(encoding="utf-8").splitlines()
            events = [json.loads(line) for line in lines]
        except (OSError, json.JSONDecodeError) as exc:
            raise PipelineError(f"Cannot load event journal {self.events_path}: {exc}") from exc
        if not all(isinstance(event, dict) for event in events):
            raise PipelineError(f"Invalid event journal: {self.events_path}")
        return events

    def _allowed_targets(
        self,
        operation: str,
        before: RunState,
        after: RunState,
    ) -> tuple[set[Path], set[Path]]:
        required = {self.events_path, self.state_path}
        optional: set[Path] = set()
        if operation == "record_evaluation":
            iteration_dir = self.run_dir / "iterations" / f"{after.iterations_completed:02d}"
            required.update(
                {
                    iteration_dir / "cv_in.md",
                    iteration_dir / "evaluation.md",
                    iteration_dir / "evaluation.json",
                    self.run_dir / "scores.csv",
                    before.data_path / "evaluation.md",
                }
            )
            if after.phase is Phase.COACHING_READY:
                required.add(before.data_path / "docs" / "cv.md")
        elif operation == "prepare_bill":
            required.add(self.run_dir / "guards" / f"bill_{before.iterations_completed:02d}.json")
        elif operation == "commit_bill":
            iteration_dir = self.run_dir / "iterations" / f"{before.iterations_completed:02d}"
            required.update({iteration_dir / "cv_out.md", before.data_path / "docs" / "cv.md"})
            optional.add(iteration_dir / "draft_notes.txt")
        elif operation == "prepare_donna":
            required.add(self.run_dir / "guards" / "donna.json")
        elif operation == "complete_donna":
            required.add(self.run_dir / "action_plan.md")
        return ({path.absolute() for path in required}, {path.absolute() for path in optional})

    def _validate_pending_state(
        self,
        manifest: PendingManifest,
        current: RunState,
        staged: RunState,
        event_payload: Path,
    ) -> None:
        if staged.revision != manifest.revision:
            raise PipelineError("Pending state revision does not match its manifest")
        identity_fields = (
            "run_id",
            "run_dir",
            "data_dir",
            "session_root",
            "agent_provider",
            "agent_model",
            "celestial_capture_id",
            "celestial_requested",
            "celestial_judge_provider",
            "celestial_judge_model",
            "max_iterations",
            "min_fit_score",
            "karen_reads_background",
            "created_at",
        )
        if any(getattr(staged, field) != getattr(current, field) for field in identity_fields):
            raise PipelineError("Pending state changes immutable run identity")
        from_phases, to_phases = TRANSITION_PHASES[manifest.operation]
        try:
            events = [json.loads(line) for line in event_payload.read_text().splitlines()]
            event = events[-1]
            event_from = Phase(event["from_phase"])
            event_to = Phase(event["to_phase"])
        except (OSError, ValueError, KeyError, IndexError, json.JSONDecodeError) as exc:
            raise PipelineError(f"Invalid pending event journal: {exc}") from exc
        published_events = self._events()
        if current.revision + 1 == manifest.revision:
            # Recovery may observe either side of the event-file replacement because
            # state.json is deliberately published last.
            if published_events not in (events[:-1], events):
                raise PipelineError("Pending event journal rewrites published history")
        elif current.revision == manifest.revision and events != published_events:
            raise PipelineError("Pending event journal conflicts with published history")
        if (
            event.get("revision") != manifest.revision
            or event.get("operation") != manifest.operation
            or event_from not in from_phases
            or event_to not in to_phases
            or event_to is not staged.phase
        ):
            raise PipelineError("Pending event does not match the declared transition")
        if manifest.operation in {"prepare_bill", "prepare_donna"}:
            reference = (
                staged.bill_guard if manifest.operation == "prepare_bill" else staged.donna_guard
            )
            details = event.get("details")
            if (
                reference is None
                or not isinstance(details, dict)
                or details.get("guard_path") != reference.path
                or details.get("guard_sha256") != reference.sha256
                or details.get("guard_revision") != reference.revision
            ):
                raise PipelineError("Pending guard reference is not anchored in its event")
        if current.revision + 1 == manifest.revision:
            if current.phase is not event_from:
                raise PipelineError("Pending operation is not valid for the current phase")
            allowed_changes = {"revision", "updated_at", "phase"}
            allowed_changes.update(
                {
                    "start_session": {"current_session_id", "current_session_dir"},
                    "record_evaluation": {
                        "outcome",
                        "iterations_completed",
                        "latest_score",
                    },
                    "prepare_bill": {"bill_guard"},
                    "prepare_donna": {"donna_guard"},
                }.get(manifest.operation, set())
            )
            current_data = current.model_dump(mode="json")
            staged_data = staged.model_dump(mode="json")
            changed = {
                field for field, value in staged_data.items() if current_data[field] != value
            }
            if not changed.issubset(allowed_changes):
                raise PipelineError("Pending state changes fields outside the operation contract")
            if manifest.operation == "record_evaluation":
                if (
                    staged.iterations_completed != current.iterations_completed + 1
                    or staged.latest_score is None
                    or (staged.phase is Phase.NEEDS_REVISION and staged.outcome is not None)
                    or (staged.phase is Phase.COACHING_READY and staged.outcome is None)
                ):
                    raise PipelineError("Pending evaluation state violates iteration invariants")
        elif current.revision == manifest.revision:
            if current.model_dump(mode="json") != staged.model_dump(mode="json"):
                raise PipelineError("Pending state conflicts with the published revision")
            if current.phase is not event_to:
                raise PipelineError("Published state conflicts with the pending operation")
        else:
            raise PipelineError("Pending revision is not adjacent to the current state")

    def _recover_pending(self) -> None:
        if not self.pending_path.is_file():
            return
        try:
            _ensure_no_symlink_components(self.pending_path)
            manifest = PendingManifest.model_validate_json(
                self.pending_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError, ValidationError) as exc:
            raise PipelineError(f"Cannot recover pending transition: {exc}") from exc
        current = self._load()
        transactions_dir = self.run_dir / "transactions"
        sources: list[Path] = []
        targets: list[Path] = []
        transaction_dir: Path | None = None
        for index, write in enumerate(manifest.writes):
            source = Path(write.source)
            target = Path(write.target)
            if (
                not source.is_absolute()
                or not target.is_absolute()
                or source.name != f"payload-{index:04d}"
                or source.parent.parent != transactions_dir
            ):
                raise PipelineError("Pending manifest contains a non-canonical path")
            if transaction_dir is None:
                transaction_dir = source.parent
                expected_prefix = f"{manifest.revision:06d}-{manifest.operation}-"
                if not transaction_dir.name.startswith(expected_prefix):
                    raise PipelineError(
                        "Pending transaction directory does not match operation and revision"
                    )
            elif source.parent != transaction_dir:
                raise PipelineError("Pending payloads must share one transaction directory")
            _ensure_no_symlink_components(source)
            try:
                source_stat = source.lstat()
            except OSError as exc:
                raise PipelineError(f"Cannot inspect pending payload {source}: {exc}") from exc
            if (
                not stat.S_ISREG(source_stat.st_mode)
                or source_stat.st_size != write.size
                or _file_sha256(source) != write.sha256
            ):
                raise PipelineError(f"Pending payload failed integrity validation: {source}")
            sources.append(source)
            targets.append(target)
        if len(set(sources)) != len(sources) or len(set(targets)) != len(targets):
            raise PipelineError("Pending manifest contains duplicate sources or targets")
        if targets[-1] != self.state_path or targets.count(self.state_path) != 1:
            raise PipelineError("Pending state.json must be unique and the final write")
        try:
            state_index = targets.index(self.state_path)
            events_index = targets.index(self.events_path)
            staged = _parse_run_state(sources[state_index].read_text(encoding="utf-8"))
        except (ValueError, ValidationError) as exc:
            raise PipelineError(f"Invalid pending canonical payload: {exc}") from exc
        self._validate_pending_state(manifest, current, staged, sources[events_index])
        required, optional = self._allowed_targets(manifest.operation, current, staged)
        target_set = set(targets)
        if not required.issubset(target_set) or not target_set.issubset(required | optional):
            raise PipelineError("Pending manifest contains targets outside the operation allowlist")
        if manifest.operation in {"prepare_bill", "prepare_donna"}:
            reference = (
                staged.bill_guard if manifest.operation == "prepare_bill" else staged.donna_guard
            )
            if reference is None:
                raise PipelineError("Pending guard reference is missing")
            guard_index = targets.index(Path(reference.path))
            if manifest.writes[guard_index].sha256 != reference.sha256:
                raise PipelineError("Pending guard payload does not match its canonical digest")
        for source, target, write in zip(sources, targets, manifest.writes, strict=True):
            _ensure_no_symlink_components(target, include_leaf=False)
            if target.is_symlink():
                raise PipelineError(f"Pending target is a symlink: {target}")
            atomic_copy(source, target)
            if target.stat().st_size != write.size or _file_sha256(target) != write.sha256:
                raise PipelineError(f"Published target failed integrity validation: {target}")
        self.pending_path.unlink()

    def load(self) -> RunState:
        with self._lock():
            self._recover_pending()
            return self._load()

    def transition(
        self,
        operation: str,
        allowed: set[Phase],
        action: Transition,
    ) -> RunState:
        with self._lock():
            self._recover_pending()
            state = self._load()
            if state.phase not in allowed:
                events = self._events()
                if events and events[-1].get("operation") == operation:
                    return state
                expected = ", ".join(sorted(phase.value for phase in allowed))
                raise PipelineError(
                    f"Transition not allowed from {state.phase.value}; expected: {expected}"
                )
            previous_phase = state.phase
            transaction = TransitionTransaction(
                self.run_dir,
                operation,
                state.revision + 1,
            )
            event, details = action(state, transaction)
            state.revision += 1
            state.updated_at = utc_now()
            events = self._events()
            events.append(
                {
                    "timestamp": state.updated_at,
                    "revision": state.revision,
                    "operation": operation,
                    "event": event,
                    "from_phase": previous_phase.value,
                    "to_phase": state.phase.value,
                    "outcome": state.outcome.value if state.outcome else None,
                    "session_id": state.current_session_id,
                    "details": details,
                }
            )
            transaction.write_text(
                self.events_path,
                "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in events),
            )
            # State is deliberately the final write: recovery can safely reapply all earlier
            # artifact replacements until this canonical pointer advances.
            transaction.write_json(self.state_path, state.model_dump(mode="json"))
            manifest = {
                "schema_version": 2,
                "operation": operation,
                "revision": state.revision,
                "writes": [
                    {
                        "source": str(write.source),
                        "target": str(write.target),
                        "size": write.size,
                        "sha256": write.sha256,
                    }
                    for write in transaction.writes
                ],
            }
            atomic_write_json(self.pending_path, manifest)
            self._recover_pending()
            return state


def _configured_path(environment_name: str, default: Path) -> Path:
    return Path(os.environ.get(environment_name, str(default))).expanduser().resolve()


def _path_snapshot(path: Path) -> dict[str, dict[str, str]]:
    """Describe a path plus the identity and resolution of every lexical ancestor."""

    def describe(item: Path) -> dict[str, str]:
        try:
            metadata = item.lstat()
        except FileNotFoundError:
            return {"type": "absent"}
        identity = {"device": str(metadata.st_dev), "inode": str(metadata.st_ino)}
        if stat.S_ISLNK(metadata.st_mode):
            return {"type": "symlink", "target": os.readlink(item), **identity}
        if stat.S_ISREG(metadata.st_mode):
            return {"type": "file", "sha256": _file_sha256(item), **identity}
        if stat.S_ISDIR(metadata.st_mode):
            return {"type": "directory", **identity}
        return {"type": "other", **identity}

    absolute = path.absolute()
    snapshot = {
        "@resolution": {"type": "resolution", "path": str(absolute.resolve(strict=False))},
        **{f"@ancestor:{ancestor}": describe(ancestor) for ancestor in reversed(absolute.parents)},
        ".": describe(absolute),
    }
    if snapshot["."]["type"] != "directory":
        return snapshot
    for child in sorted(absolute.rglob("*"), key=lambda item: item.as_posix()):
        snapshot[child.relative_to(absolute).as_posix()] = describe(child)
    return snapshot


def _bill_protected_paths(state: RunState) -> dict[str, Path]:
    session = state.session_path
    layout = SessionLayout(session)
    docs = state.data_path / "docs"
    return {
        "session_job": session / "docs" / "job.md",
        "session_company_info": session / "company_info.md",
        "session_background_public": session / "docs" / "who_are_u.md",
        "session_background_private": layout.artifacts / "who_are_u.md",
        "session_evaluation": layout.artifacts / "karen_output.md",
        "session_repositories": session / "repos",
        "session_repositories_json": session / "repos.json",
        "session_repositories_count": session / "repos_expected_count.txt",
        "canonical_cv": docs / "cv.md",
        "canonical_job": docs / "job.md",
        "canonical_background": docs / "who_are_u.md",
    }


def _donna_protected_paths(state: RunState) -> dict[str, Path]:
    session = state.session_path
    docs = state.data_path / "docs"
    final_iteration = state.run_path / "iterations" / f"{state.iterations_completed:02d}"
    return {
        "session_cv": session / "docs" / "cv.md",
        "session_job": session / "docs" / "job.md",
        "session_repositories": session / "repos",
        "canonical_cv": docs / "cv.md",
        "canonical_job": docs / "job.md",
        "final_evaluation": final_iteration / "evaluation.md",
    }


def _snapshots(paths: dict[str, Path]) -> dict[str, dict[str, dict[str, str]]]:
    return {name: _path_snapshot(path) for name, path in paths.items()}


def _ancestor_snapshot(snapshot: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    return {name: value for name, value in snapshot.items() if name.startswith("@")}


def _repository_snapshot(root: Path = REPOSITORY_ROOT) -> dict[str, dict[str, str]]:
    """Snapshot every tracked or non-ignored worktree path, including missing files."""

    result = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        error = result.stderr.decode(errors="replace").strip()
        raise PipelineError(f"Cannot snapshot host repository: {error}")
    snapshot: dict[str, dict[str, str]] = {}
    for raw_name in result.stdout.split(b"\0"):
        if not raw_name:
            continue
        name = raw_name.decode("utf-8", errors="surrogateescape")
        snapshot[name] = _path_snapshot(root / name)["."]
    return snapshot


def _state_payload(state_path: Path, state: RunState) -> dict[str, Any]:
    return {"state_path": str(state_path.resolve()), **state.model_dump(mode="json")}


def initialize_run(
    *,
    max_iterations: int,
    min_fit_score: int,
    karen_reads_background: bool,
    agent_provider: Literal["agy", "claude", "codex", "replay"] = "agy",
    agent_model: str | None = None,
    celestial_capture_id: str | None = None,
    celestial_requested: bool = False,
    celestial_judge_provider: Literal["agy", "claude", "codex"] | None = None,
    celestial_judge_model: str | None = None,
    run_id: str | None = None,
) -> tuple[Path, RunState]:
    data_dir = _configured_path("PIPELINE_DATA_DIR", REPOSITORY_ROOT / ".data")
    runs_dir = _configured_path("PIPELINE_RUNS_DIR", REPOSITORY_ROOT / ".runs")
    session_root = _configured_path("PIPELINE_SESSION_ROOT", Path("/tmp"))
    docs_dir = data_dir / "docs"
    cv_path = docs_dir / "cv.md"
    job_path = docs_dir / "job.md"
    for path in (cv_path, job_path):
        if not path.is_file() or path.stat().st_size < 10:
            raise PipelineError(f"Required input is missing or too small: {path}")
    first_line = job_path.read_text(encoding="utf-8").splitlines()[0]
    if JOB_HEADER.fullmatch(first_line) is None:
        raise PipelineError("job.md must start with '# <Position> — <Company>'")

    if run_id is None:
        run_id = f"{utc_now()[:19].replace(':', '').replace('-', '')}_{uuid.uuid4().hex[:6]}"
    if RUN_ID.fullmatch(run_id) is None:
        raise PipelineError(f"Invalid run ID: {run_id!r}")
    run_dir = runs_dir / run_id
    now = utc_now()
    try:
        state = RunState(
            run_id=run_id,
            run_dir=str(run_dir),
            data_dir=str(data_dir),
            session_root=str(session_root),
            agent_provider=agent_provider,
            agent_model=agent_model,
            celestial_capture_id=celestial_capture_id,
            celestial_requested=celestial_requested,
            celestial_judge_provider=celestial_judge_provider,
            celestial_judge_model=celestial_judge_model,
            max_iterations=max_iterations,
            min_fit_score=min_fit_score,
            karen_reads_background=karen_reads_background,
            created_at=now,
            updated_at=now,
        )
    except ValidationError as exc:
        raise PipelineError(f"Invalid run configuration: {exc}") from exc

    runs_dir.mkdir(parents=True, exist_ok=True)
    lock_path = runs_dir / ".initialize.lock"
    with lock_path.open("a+") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        if run_dir.exists():
            raise PipelineError(f"Run already exists: {run_dir}")
        staging = Path(tempfile.mkdtemp(prefix=f".{run_id}.", dir=runs_dir))
        atomic_write_json(staging / "state.json", state.model_dump(mode="json"))
        atomic_write_text(staging / "scores.csv", "iteration,score\n")
        event = {
            "timestamp": now,
            "revision": 0,
            "operation": "initialize_run",
            "event": "run_initialized",
            "from_phase": None,
            "to_phase": state.phase.value,
            "outcome": None,
            "session_id": None,
            "details": {
                "max_iterations": max_iterations,
                "min_fit_score": min_fit_score,
                "agent_provider": agent_provider,
                "agent_model": agent_model,
                "celestial_capture_id": celestial_capture_id,
                "celestial_requested": celestial_requested,
            },
        }
        atomic_write_text(staging / "events.jsonl", json.dumps(event) + "\n")
        staging.rename(run_dir)
        directory_fd = os.open(runs_dir, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    state_path = run_dir / "state.json"
    if celestial_capture_id is not None:
        create_run_request(
            capture_id=celestial_capture_id,
            run_id=run_id,
            run_dir=str(run_dir),
            subject_provider=agent_provider,
            subject_model=agent_model,
            celestial_requested=celestial_requested,
            judge_provider=celestial_judge_provider,
            judge_model=celestial_judge_model,
        )
        record_envelope(
            capture_id=celestial_capture_id,
            run_id=run_id,
            role=AgentRole.VERA,
            invocation=1,
            instruction=None,
            inputs={},
            outputs={},
            status=EnvelopeStatus.NOT_OBSERVED,
        )
        record_case_input(
            celestial_capture_id,
            "initial_cv",
            cv_path.read_text(encoding="utf-8"),
        )
        record_case_input(
            celestial_capture_id,
            "job_description",
            job_path.read_text(encoding="utf-8"),
        )
    return state_path, state


def _existing_texts(paths: dict[str, Path]) -> dict[str, str]:
    values: dict[str, str] = {}
    for label, path in paths.items():
        content = read_text_if_file(path)
        if content is not None:
            values[label] = content
    return values


def _capture_agent(
    state: RunState,
    *,
    role: AgentRole,
    invocation: int,
    instruction_path: Path,
    inputs: dict[str, Path],
    outputs: dict[str, Path],
    coverage: Coverage = Coverage.PROMPT_OUTPUT_ONLY,
) -> bool:
    if state.celestial_capture_id is None:
        return True
    instruction = read_text_if_file(instruction_path)
    try:
        record_envelope(
            capture_id=state.celestial_capture_id,
            run_id=state.run_id,
            role=role,
            invocation=invocation,
            instruction=(f"{role.value}_instruction", instruction)
            if instruction is not None
            else None,
            inputs=_existing_texts(inputs),
            outputs=_existing_texts(outputs),
            coverage=coverage,
        )
    except (OSError, ValueError) as exc:
        print(f"Celestial capture warning for {role.value}: {exc}", file=sys.stderr)
        try:
            update_request(
                state.celestial_capture_id,
                status="capture_incomplete",
                last_capture_error=str(exc),
            )
        except (OSError, ValueError):
            pass
        return False
    return True


def start_session(store: RunStore) -> RunState:
    def action(state: RunState, transaction: TransitionTransaction) -> tuple[str, dict[str, Any]]:
        del transaction
        harvey = Harvey.setup(
            data_dir=state.data_path,
            session_root=Path(state.session_root),
            karen_reads_background=state.karen_reads_background,
        )
        harvey.setup_paths().ingest_documents()
        layout = SessionLayout(harvey.session_dir)
        render_agent(
            "shadow",
            {"session_id": harvey.session_id, "session_dir": str(harvey.session_dir)},
            REPOSITORY_ROOT / "harvey_guy" / "shadow.md",
            layout.contracts / "shadow",
        )
        state.current_session_id = harvey.session_id
        state.current_session_dir = str(harvey.session_dir)
        state.phase = Phase.SHADOW_RUNNING
        return "session_started", {"session_dir": str(harvey.session_dir)}

    return store.transition("start_session", {Phase.READY}, action)


def mark_shadow_ready(store: RunStore) -> RunState:
    def action(state: RunState, transaction: TransitionTransaction) -> tuple[str, dict[str, Any]]:
        del transaction
        session = state.session_path
        company_info = session / "company_info.md"
        if not company_info.is_file() or company_info.stat().st_size < 100:
            raise PipelineError(f"Company research missing or too small: {company_info}")
        repos_json = session / "repos.json"
        count_path = session / "repos_expected_count.txt"
        try:
            repositories = json.loads(repos_json.read_text(encoding="utf-8"))
            expected = int(count_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise PipelineError(f"Invalid repository inventory: {exc}") from exc
        if not isinstance(repositories, list) or not all(
            isinstance(repository, dict) and isinstance(repository.get("clone_url"), str)
            for repository in repositories
        ):
            raise PipelineError("repos.json must be an array of repositories with clone_url")
        actual = len([path for path in (session / "repos").iterdir() if path.is_dir()])
        if expected != len(repositories) or actual != expected:
            raise PipelineError(
                f"Repository inventory mismatch: json={len(repositories)}, "
                f"expected={expected}, cloned={actual}"
            )
        warnings = SessionLayout(session).logs / "clone_warnings.txt"
        if warnings.exists():
            raise PipelineError(f"Clone warnings must be resolved before evaluation: {warnings}")
        state.phase = Phase.KAREN_READY
        return "shadow_completed", {"repository_count": actual}

    state = store.transition("mark_shadow_ready", {Phase.SHADOW_RUNNING}, action)
    session = state.session_path
    _capture_agent(
        state,
        role=AgentRole.SHADOW,
        invocation=state.iterations_completed + 1,
        instruction_path=SessionLayout(session).contracts / "shadow" / "shadow.prompt",
        inputs={
            "cv": session / "docs" / "cv.md",
            "job_description": session / "docs" / "job.md",
            "candidate_background": session / "docs" / "who_are_u.md",
        },
        outputs={
            "company_sources": session / "company_info.md",
            "repository_inventory": session / "repos.json",
        },
    )
    return state


def record_evaluation(store: RunStore) -> RunState:
    def action(state: RunState, transaction: TransitionTransaction) -> tuple[str, dict[str, Any]]:
        session = state.session_path
        report = SessionLayout(session).artifacts / "karen_output.md"
        evaluation = read_evaluation(report)
        iteration = state.iterations_completed + 1
        iteration_dir = state.run_path / "iterations" / f"{iteration:02d}"
        transaction.copy(session / "docs" / "cv.md", iteration_dir / "cv_in.md")
        transaction.copy(report, iteration_dir / "evaluation.md")
        transaction.copy(report, state.data_path / "evaluation.md")
        transaction.write_json(
            iteration_dir / "evaluation.json", evaluation.model_dump(mode="json")
        )
        score_rows = ["iteration,score"]
        for completed in range(1, iteration):
            evaluation_path = state.run_path / "iterations" / f"{completed:02d}" / "evaluation.json"
            try:
                archived = json.loads(evaluation_path.read_text(encoding="utf-8"))
                score_rows.append(f"{completed},{int(archived['fit_score'])}")
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                raise PipelineError(f"Cannot derive score history: {exc}") from exc
        score_rows.append(f"{iteration},{evaluation.fit_score}")
        transaction.write_text(state.run_path / "scores.csv", "\n".join(score_rows) + "\n")

        state.iterations_completed = iteration
        state.latest_score = evaluation.fit_score
        if evaluation.fit_score >= state.min_fit_score:
            state.outcome = Outcome.SUCCESS
            state.phase = Phase.COACHING_READY
            transaction.copy(session / "docs" / "cv.md", state.data_path / "docs" / "cv.md")
        elif iteration >= state.max_iterations:
            state.outcome = Outcome.MAX_ITERATIONS
            state.phase = Phase.COACHING_READY
            transaction.copy(session / "docs" / "cv.md", state.data_path / "docs" / "cv.md")
        else:
            state.phase = Phase.NEEDS_REVISION
        return (
            "evaluation_recorded",
            {
                "iteration": iteration,
                "fit_score": evaluation.fit_score,
                "report_sha256": evaluation.report_sha256,
            },
        )

    state = store.transition("record_evaluation", {Phase.KAREN_READY}, action)
    session = state.session_path
    iteration_dir = state.run_path / "iterations" / f"{state.iterations_completed:02d}"
    _capture_agent(
        state,
        role=AgentRole.KAREN,
        invocation=state.iterations_completed,
        instruction_path=REPOSITORY_ROOT / "karen_guard" / "prompt_persona.txt",
        inputs={
            "cv": iteration_dir / "cv_in.md",
            "job_description": session / "docs" / "job.md",
            "company_research": session / "company_info.md",
            "candidate_background": session / "docs" / "who_are_u.md",
        },
        outputs={"evaluation": iteration_dir / "evaluation.md"},
    )
    return state


def prepare_bill(store: RunStore) -> RunState:
    def action(state: RunState, transaction: TransitionTransaction) -> tuple[str, dict[str, Any]]:
        session = state.session_path
        layout = SessionLayout(session)
        protected_paths = _bill_protected_paths(state)
        cv_path = session / "docs" / "cv.md"
        _ensure_regular_file(cv_path, "Bill input CV")
        guard = BillGuard(
            run_id=state.run_id,
            revision=state.revision + 1,
            iteration=state.iterations_completed,
            cv_sha256=_file_sha256(cv_path),
            protected=_snapshots(protected_paths),
            host_repository=_repository_snapshot(),
        )
        guard_path = state.run_path / "guards" / f"bill_{state.iterations_completed:02d}.json"
        guard_text = _json_text(guard.model_dump(mode="json"))
        guard_sha256 = _text_sha256(guard_text)
        transaction.write_text(guard_path, guard_text)
        state.bill_guard = GuardReference(
            kind="bill",
            path=str(guard_path),
            sha256=guard_sha256,
            revision=state.revision + 1,
        )

        background = protected_paths["session_background_private"]
        if not background.is_file():
            background = protected_paths["session_background_public"]
        render_agent(
            "bill",
            {
                "session_id": state.current_session_id,
                "session_dir": str(session),
                "karen_report_path": str(protected_paths["session_evaluation"]),
                "candidate_background_path": str(background) if background.is_file() else None,
            },
            REPOSITORY_ROOT / "billf" / "main.md",
            layout.contracts / "bill",
        )
        state.phase = Phase.BILL_RUNNING
        return "bill_prepared", {
            "guard_path": str(guard_path),
            "guard_sha256": guard_sha256,
            "guard_revision": state.revision + 1,
        }

    return store.transition("prepare_bill", {Phase.NEEDS_REVISION}, action)


def commit_bill(store: RunStore) -> RunState:
    def action(state: RunState, transaction: TransitionTransaction) -> tuple[str, dict[str, Any]]:
        session = state.session_path
        layout = SessionLayout(session)
        guard_path = state.run_path / "guards" / f"bill_{state.iterations_completed:02d}.json"
        reference = state.bill_guard
        if (
            reference is None
            or reference.kind != "bill"
            or Path(reference.path) != guard_path
            or reference.revision != state.revision
        ):
            raise PipelineError("Bill guard reference does not match the active revision")
        try:
            guard_text = guard_path.read_text(encoding="utf-8")
            if _text_sha256(guard_text) != reference.sha256:
                raise PipelineError("Bill guard digest does not match canonical state")
            guard = BillGuard.model_validate_json(guard_text)
        except (OSError, ValueError, ValidationError) as exc:
            raise PipelineError(f"Cannot load Bill guard: {exc}") from exc
        if (
            guard.run_id != state.run_id
            or guard.revision != reference.revision
            or guard.iteration != state.iterations_completed
        ):
            raise PipelineError("Bill guard identity does not match the active run")
        cv_path = session / "docs" / "cv.md"
        _ensure_regular_file(cv_path, "Bill output CV")
        current_cv_hash = _file_sha256(cv_path)
        if current_cv_hash == guard.cv_sha256:
            raise PipelineError("Bill did not modify the CV")

        protected_paths = _bill_protected_paths(state)
        current_protected = _snapshots(protected_paths)
        if current_protected != guard.protected:
            raise PipelineError("Bill modified a protected context file")
        if _repository_snapshot() != guard.host_repository:
            raise PipelineError("Bill modified the host repository")

        iteration_dir = state.run_path / "iterations" / f"{state.iterations_completed:02d}"
        transaction.copy(cv_path, iteration_dir / "cv_out.md")
        draft_notes = layout.artifacts / "draft_notes.txt"
        if draft_notes.is_file():
            transaction.copy(draft_notes, iteration_dir / "draft_notes.txt")
        transaction.copy(cv_path, state.data_path / "docs" / "cv.md")
        state.phase = Phase.READY
        return "bill_committed", {"cv_sha256": current_cv_hash}

    state = store.transition("commit_bill", {Phase.BILL_RUNNING}, action)
    iteration_dir = state.run_path / "iterations" / f"{state.iterations_completed:02d}"
    _capture_agent(
        state,
        role=AgentRole.BILL,
        invocation=state.iterations_completed,
        instruction_path=SessionLayout(state.session_path).contracts / "bill" / "bill.prompt",
        inputs={
            "cv_before": iteration_dir / "cv_in.md",
            "karen_report": iteration_dir / "evaluation.md",
            "candidate_background": state.session_path / "docs" / "who_are_u.md",
        },
        outputs={
            "cv_after": iteration_dir / "cv_out.md",
            "draft_notes": iteration_dir / "draft_notes.txt",
        },
    )
    return state


def prepare_donna(store: RunStore) -> RunState:
    def action(state: RunState, transaction: TransitionTransaction) -> tuple[str, dict[str, Any]]:
        if state.latest_score is None:
            raise PipelineError("Cannot prepare Donna without a fit score")
        session = state.session_path
        layout = SessionLayout(session)
        action_plan = state.data_path / "docs" / "action_plan.md"
        guard_path = state.run_path / "guards" / "donna.json"
        guard = DonnaGuard(
            run_id=state.run_id,
            revision=state.revision + 1,
            action_plan_before=_path_snapshot(action_plan),
            protected=_snapshots(_donna_protected_paths(state)),
            host_repository=_repository_snapshot(),
        )
        guard_text = _json_text(guard.model_dump(mode="json"))
        guard_sha256 = _text_sha256(guard_text)
        transaction.write_text(guard_path, guard_text)
        state.donna_guard = GuardReference(
            kind="donna",
            path=str(guard_path),
            sha256=guard_sha256,
            revision=state.revision + 1,
        )
        final_report = (
            state.run_path / "iterations" / f"{state.iterations_completed:02d}" / "evaluation.md"
        )
        render_agent(
            "donna",
            {
                "session_id": state.current_session_id,
                "session_dir": str(session),
                "karen_report_path": str(final_report),
                "action_plan_path": str(action_plan),
                "fit_score": state.latest_score,
                "min_fit_score": state.min_fit_score,
            },
            REPOSITORY_ROOT / "donna_nana" / "main.md",
            layout.contracts / "donna",
        )
        state.phase = Phase.DONNA_RUNNING
        return "donna_prepared", {
            "guard_path": str(guard_path),
            "guard_sha256": guard_sha256,
            "guard_revision": state.revision + 1,
        }

    return store.transition("prepare_donna", {Phase.COACHING_READY}, action)


def complete_donna(store: RunStore) -> RunState:
    def action(state: RunState, transaction: TransitionTransaction) -> tuple[str, dict[str, Any]]:
        action_plan = state.data_path / "docs" / "action_plan.md"
        _ensure_regular_file(action_plan, "Donna action plan")
        if action_plan.stat().st_size < 100:
            raise PipelineError(f"Action plan missing or too small: {action_plan}")
        if not action_plan.read_text(encoding="utf-8").startswith("#"):
            raise PipelineError("Action plan must start with a Markdown heading")
        guard_path = state.run_path / "guards" / "donna.json"
        reference = state.donna_guard
        if (
            reference is None
            or reference.kind != "donna"
            or Path(reference.path) != guard_path
            or reference.revision != state.revision
        ):
            raise PipelineError("Donna guard reference does not match the active revision")
        try:
            guard_text = guard_path.read_text(encoding="utf-8")
            if _text_sha256(guard_text) != reference.sha256:
                raise PipelineError("Donna guard digest does not match canonical state")
            guard = DonnaGuard.model_validate_json(guard_text)
        except (OSError, ValueError, ValidationError) as exc:
            raise PipelineError(f"Cannot load Donna guard: {exc}") from exc
        if guard.run_id != state.run_id or guard.revision != reference.revision:
            raise PipelineError("Donna guard identity does not match the active run")
        if _snapshots(_donna_protected_paths(state)) != guard.protected:
            raise PipelineError("Donna modified a protected context file")
        if _repository_snapshot() != guard.host_repository:
            raise PipelineError("Donna modified the host repository")
        current_plan = _path_snapshot(action_plan)
        if _ancestor_snapshot(current_plan) != _ancestor_snapshot(guard.action_plan_before):
            raise PipelineError("Donna action-plan ancestors changed after preparation")
        previous_leaf = guard.action_plan_before["."]
        current_leaf = current_plan["."]
        if current_leaf == previous_leaf or (
            previous_leaf.get("type") == "file"
            and current_leaf.get("sha256") == previous_leaf.get("sha256")
        ):
            raise PipelineError("Donna did not create or change the action plan")
        archived_plan = state.run_path / "action_plan.md"
        transaction.copy(action_plan, archived_plan)
        state.phase = Phase.COMPLETE
        return "run_completed", {
            "action_plan": str(action_plan),
            "archived_action_plan": str(archived_plan),
            "action_plan_sha256": _file_sha256(action_plan),
        }

    state = store.transition("complete_donna", {Phase.DONNA_RUNNING}, action)
    iteration_dir = state.run_path / "iterations" / f"{state.iterations_completed:02d}"
    donna_captured = _capture_agent(
        state,
        role=AgentRole.DONNA,
        invocation=1,
        instruction_path=SessionLayout(state.session_path).contracts / "donna" / "donna.prompt",
        inputs={
            "final_cv": state.data_path / "docs" / "cv.md",
            "final_evaluation": iteration_dir / "evaluation.md",
            "job_description": state.data_path / "docs" / "job.md",
        },
        outputs={"action_plan": state.run_path / "action_plan.md"},
    )
    harvey_captured = _capture_agent(
        state,
        role=AgentRole.HARVEY,
        invocation=1,
        instruction_path=REPOSITORY_ROOT / "harvey_guy" / "main.md",
        inputs={
            "initial_job": state.data_path / "docs" / "job.md",
            "final_cv": state.data_path / "docs" / "cv.md",
        },
        outputs={
            "final_evaluation": iteration_dir / "evaluation.md",
            "action_plan": state.run_path / "action_plan.md",
        },
        coverage=Coverage.ORCHESTRATION_BUNDLE,
    )
    if state.celestial_capture_id is not None:
        try:
            record_case_input(
                state.celestial_capture_id,
                "final_cv",
                (state.data_path / "docs" / "cv.md").read_text(encoding="utf-8"),
            )
            update_request(state.celestial_capture_id, status="capture_complete")
            repository_roots = [
                path for path in (state.session_path / "repos").iterdir() if path.is_dir()
            ]
            case_root = freeze_capture(
                state.celestial_capture_id,
                evidence_roots=repository_roots,
            )
            request = read_celestial_json(capture_root(state.celestial_capture_id) / "request.json")
            update_request(
                state.celestial_capture_id,
                status=("ready" if state.celestial_requested else "captured_disabled")
                if donna_captured and harvey_captured and "last_capture_error" not in request
                else "ready_with_capture_errors",
                case_id=case_root.name,
            )
        except (OSError, ValueError) as exc:
            print(f"Celestial freeze warning: {exc}", file=sys.stderr)
    return state


def _add_state_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state", required=True, type=Path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic Crime Alley control plane")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    init.add_argument("--max-iterations", required=True, type=int)
    init.add_argument("--min-fit-score", required=True, type=int)
    init.add_argument("--karen-reads-background", choices=("yes", "no"), required=True)
    init.add_argument("--agent-provider", choices=("agy", "claude", "codex"), default="agy")
    init.add_argument("--agent-model")
    init.add_argument("--celestial-capture-id")
    init.add_argument("--celestial-enabled", action="store_true")
    init.add_argument("--celestial-judge-provider", choices=("agy", "claude", "codex"))
    init.add_argument("--celestial-judge-model")
    init.add_argument("--run-id")

    for name in (
        "start-session",
        "shadow-ready",
        "record-evaluation",
        "prepare-bill",
        "commit-bill",
        "prepare-donna",
        "complete-donna",
        "status",
    ):
        _add_state_argument(commands.add_parser(name))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        if args.command == "init":
            state_path, state = initialize_run(
                max_iterations=args.max_iterations,
                min_fit_score=args.min_fit_score,
                karen_reads_background=args.karen_reads_background == "yes",
                agent_provider=args.agent_provider,
                agent_model=args.agent_model,
                celestial_capture_id=args.celestial_capture_id,
                celestial_requested=args.celestial_enabled,
                celestial_judge_provider=args.celestial_judge_provider,
                celestial_judge_model=args.celestial_judge_model,
                run_id=args.run_id,
            )
        else:
            state_path = args.state
            store = RunStore(state_path)
            commands: dict[str, Callable[[RunStore], RunState]] = {
                "start-session": start_session,
                "shadow-ready": mark_shadow_ready,
                "record-evaluation": record_evaluation,
                "prepare-bill": prepare_bill,
                "commit-bill": commit_bill,
                "prepare-donna": prepare_donna,
                "complete-donna": complete_donna,
                "status": lambda current_store: current_store.load(),
            }
            state = commands[args.command](store)
        print(json.dumps(_state_payload(state_path, state), ensure_ascii=False))
    except (OSError, PipelineError, ValidationError, ValueError) as exc:
        print(f"Pipeline error: {exc}", file=sys.stderr)
        raise SystemExit(3) from exc


if __name__ == "__main__":
    main()
