"""Replay recorded Karen reports through the deterministic control plane."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from harvey_guy.audit import append_boundary_event
from harvey_guy.finalize_run import finalize_run
from harvey_guy.io import atomic_copy
from harvey_guy.layout import SessionLayout
from harvey_guy.pipeline import (
    Phase,
    PipelineError,
    RunStore,
    commit_bill,
    complete_donna,
    initialize_run,
    mark_shadow_ready,
    prepare_bill,
    prepare_donna,
    record_evaluation,
    start_session,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REAL_DATA_DIR = (REPOSITORY_ROOT / ".data").resolve()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", required=True, type=Path)
    parser.add_argument("--max-iterations", required=True, type=int)
    parser.add_argument("--min-fit-score", required=True, type=int)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def _prepare_root(requested: Path | None) -> Path:
    if requested is None:
        return Path(tempfile.mkdtemp(prefix="meta-2028-replay-"))
    root = requested.expanduser().resolve()
    if root == REAL_DATA_DIR or REAL_DATA_DIR in root.parents:
        raise PipelineError(f"Refusing to replay inside real data: {root}")
    root.mkdir(parents=True, exist_ok=False)
    return root


def main() -> None:
    args = _parse_args()
    root = _prepare_root(args.output_dir)
    data_dir = root / "data"
    docs = data_dir / "docs"
    docs.mkdir(parents=True)
    atomic_copy(REPOSITORY_ROOT / "data_example" / "docs" / "cv.md", docs / "cv.md")
    atomic_copy(REPOSITORY_ROOT / "data_example" / "docs" / "job.md", docs / "job.md")
    background = REPOSITORY_ROOT / "data_example" / "docs" / "who_are_u.md"
    if background.is_file():
        atomic_copy(background, docs / "who_are_u.md")

    os.environ["PIPELINE_DATA_DIR"] = str(data_dir)
    os.environ["PIPELINE_RUNS_DIR"] = str(root / "runs")
    os.environ["PIPELINE_SESSION_ROOT"] = str(root / "sessions")
    state_path, _ = initialize_run(
        max_iterations=args.max_iterations,
        min_fit_score=args.min_fit_score,
        karen_reads_background=False,
        agent_provider="replay",
        run_id="replay",
    )
    store = RunStore(state_path)
    append_boundary_event(
        state_path.parent,
        script="replay_pipeline.py",
        mode="--offline",
        transition="initialize_replay",
        session_id=None,
        exit_code=0,
        details="Deterministic replay started.",
    )

    for report in args.report:
        session = start_session(store).session_path
        (session / "company_info.md").write_text(
            "# Replay company\n\n" + "Recorded deterministic context. " * 5,
            encoding="utf-8",
        )
        (session / "repos.json").write_text("[]\n", encoding="utf-8")
        (session / "repos_expected_count.txt").write_text("0\n", encoding="utf-8")
        mark_shadow_ready(store)
        atomic_copy(report.resolve(), SessionLayout(session).artifacts / "karen_output.md")
        state = record_evaluation(store)
        if state.phase is Phase.COACHING_READY:
            break
        prepare_bill(store)
        cv = session / "docs" / "cv.md"
        cv.write_text(
            cv.read_text(encoding="utf-8")
            + f"\nReplay revision after evaluation {state.iterations_completed}.\n",
            encoding="utf-8",
        )
        commit_bill(store)
    else:
        raise PipelineError("Replay reports were exhausted before a terminal outcome")

    prepare_donna(store)
    (docs / "action_plan.md").write_text(
        "# Replay Action Plan\n\n" + "Deterministic offline validation completed. " * 5,
        encoding="utf-8",
    )
    state = complete_donna(store)
    append_boundary_event(
        state_path.parent,
        script="replay_pipeline.py",
        mode="--offline",
        transition="finalize_replay",
        session_id=state.current_session_id,
        exit_code=0,
        details="Deterministic replay completed.",
    )
    log_tree = finalize_run(state_path)
    print(
        json.dumps(
            {
                "output_dir": str(root),
                "state_path": str(state_path),
                "outcome": state.outcome,
                "iterations_completed": state.iterations_completed,
                "latest_score": state.latest_score,
                "log_tree": str(log_tree),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
