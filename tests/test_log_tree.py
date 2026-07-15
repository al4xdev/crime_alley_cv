from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from harvey_guy.finalize_run import finalize_run
from harvey_guy.pipeline import Phase, RunStore, initialize_run, start_session

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _configure_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs = tmp_path / "data" / "docs"
    docs.mkdir(parents=True)
    (docs / "cv.md").write_text(
        "# Candidate\n\nExperienced Python platform engineer.\n", encoding="utf-8"
    )
    (docs / "job.md").write_text(
        "# Platform Engineer — Acme\n\nBuild reliable systems.\n", encoding="utf-8"
    )
    monkeypatch.setenv("PIPELINE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PIPELINE_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("PIPELINE_SESSION_ROOT", str(tmp_path / "sessions"))


def _run_boundary(script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "UV_CACHE_DIR": "/tmp/meta-2028-test-uv-cache"}
    return subprocess.run(
        ["fish", str(REPOSITORY_ROOT / "boundaries" / script), *arguments],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )


def test_finalizer_merges_timeline_and_archives_private_session_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=1,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="tree-test",
    )
    session = start_session(RunStore(state_path)).session_path
    logs = session / "anti_karen" / "logs"
    (logs / "karen.stdout.log").write_text("evaluator output\n", encoding="utf-8")
    artifacts = session / "anti_karen" / "artifacts"
    (artifacts / "note.txt").write_text("private evidence\n", encoding="utf-8")

    run_dir = state_path.parent
    audit = run_dir / "logs" / "boundary_audit.jsonl"
    audit.parent.mkdir(parents=True)
    audit.write_text(
        json.dumps(
            {
                "timestamp": "2026-07-15T12:00:00.000Z",
                "script": "harvey_setup.fish",
                "mode": "--post",
                "transition": "start_session",
                "session_id": session.name.removeprefix("karen_guard_"),
                "exit_code": 0,
                "status": "PASS",
                "details": "Transition completed.",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    tree_path = finalize_run(state_path)
    tree = tree_path.read_text(encoding="utf-8")
    archived = run_dir / "sessions" / session.name.removeprefix("karen_guard_")

    assert "run_initialized" in tree
    assert "session_started" in tree
    assert "harvey_setup.fish --post" in tree
    assert "Durable artifact tree" in tree
    assert (archived / "logs" / "karen.stdout.log").read_text() == "evaluator output\n"
    assert (archived / "artifacts" / "note.txt").read_text() == "private evidence\n"
    assert "evaluator output" in (run_dir / "logs" / "pipeline.log").read_text()


def test_boundary_scripts_validate_phase_transition_and_write_run_scoped_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=1,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="boundary-test",
    )

    initialized = _run_boundary("run_audit.fish", "--init", str(state_path))
    assert initialized.returncode == 0, initialized.stderr
    checked = _run_boundary("harvey_setup.fish", "--pre", str(state_path))
    assert checked.returncode == 0, checked.stderr
    transitioned = _run_boundary("harvey_setup.fish", "--post", str(state_path))
    assert transitioned.returncode == 0, transitioned.stderr
    assert json.loads(transitioned.stdout)["phase"] == Phase.SHADOW_RUNNING

    events = [
        json.loads(line)
        for line in (state_path.parent / "logs" / "boundary_audit.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [event["script"] for event in events] == [
        "run_audit.fish",
        "harvey_setup.fish",
        "harvey_setup.fish",
    ]
    assert all(event["status"] == "PASS" for event in events)
    assert RunStore(state_path).load().phase is Phase.SHADOW_RUNNING

    finalized = _run_boundary("run_audit.fish", "--finalize", str(state_path))
    assert finalized.returncode == 0, finalized.stderr
    tree = (state_path.parent / "log_tree.md").read_text(encoding="utf-8")
    assert "Final log consolidation started." in tree
    assert "harvey_setup.fish --post" in tree
    assert "sessions/" in tree
