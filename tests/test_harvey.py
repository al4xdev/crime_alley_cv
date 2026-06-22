from __future__ import annotations

import shutil
import uuid as uuidlib
from pathlib import Path

import pytest

from harvey_guy.harvey_guy import Harvey
from harvey_guy.libs import Log


@pytest.fixture
def harvey(tmp_path: Path) -> Harvey:
    h = Harvey()
    h.root_dir = tmp_path
    h.data_dir = tmp_path / ".data"
    h.docs_dir = h.data_dir / "docs"
    h.session_dir = tmp_path / "session"
    h.session_docs_dir = h.session_dir / "docs"
    h.repos_dir = h.session_dir / "repos"
    h.docs_dir.mkdir(parents=True)
    (h.session_dir / "anti_karen").mkdir(parents=True)
    h.log = Log.config(tmp_path / "test.log", tool=f"test-{tmp_path.name}")
    return h


def _seed_required(harvey: Harvey) -> None:
    (harvey.docs_dir / "cv.md").write_text("CV", encoding="utf-8")
    (harvey.docs_dir / "job.md").write_text("JOB", encoding="utf-8")


def test_get_root_dir_defaults_to_repo_root():
    root = Harvey()._get_root_dir(None)
    assert (root / "harvey_guy" / "harvey_guy.py").exists()


def test_get_root_dir_resolves_explicit_path(tmp_path: Path):
    assert Harvey()._get_root_dir(str(tmp_path)) == tmp_path.resolve()


def test_get_paths_is_fluent_and_derives_layout(tmp_path: Path):
    h = Harvey()
    result = h._get_paths(str(tmp_path))
    assert result is h
    assert h.data_dir == tmp_path.resolve() / ".data"
    assert h.docs_dir == tmp_path.resolve() / ".data" / "docs"


def test_init_session_creates_protected_layout():
    session_id, session_dir, log = Harvey()._init_session()
    try:
        assert uuidlib.UUID(session_id)
        assert session_dir == Path("/tmp") / f"karen_guard_{session_id}"
        assert session_dir.is_dir()
        assert (session_dir / "anti_karen").is_dir()
        assert isinstance(log, Log)
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)


def test_init_session_carry_forward(tmp_path, monkeypatch):
    import json
    # Set up a dummy previous session
    prev_session_id = "test-prev-session-123"
    prev_session_dir = Path("/tmp") / f"karen_guard_{prev_session_id}"
    prev_anti_karen = prev_session_dir / "anti_karen"
    prev_anti_karen.mkdir(parents=True, exist_ok=True)
    
    # Create some files in prev_anti_karen
    (prev_anti_karen / "draft_notes.txt").write_text("my notes", encoding="utf-8")
    (prev_anti_karen / "karen_guard_core.log").write_text("core log", encoding="utf-8")
    (prev_anti_karen / "karen_run.log").write_text("run log", encoding="utf-8")
    
    # Create the loop state checkpoint
    checkpoint_path = tmp_path / "karen_guard_loop_state.json"
    checkpoint_path.write_text(json.dumps({"session_id": prev_session_id}), encoding="utf-8")
    monkeypatch.setenv("LOOP_STATE_PATH", str(checkpoint_path))
    
    try:
        session_id, session_dir, log = Harvey()._init_session()
        try:
            anti_karen_dir = session_dir / "anti_karen"
            assert (anti_karen_dir / "draft_notes.txt").read_text(encoding="utf-8") == "my notes"
            core_path = anti_karen_dir / "karen_guard_core_prev.log"
            assert core_path.read_text(encoding="utf-8") == "core log"
            run_path = anti_karen_dir / "karen_run_prev.log"
            assert run_path.read_text(encoding="utf-8") == "run log"
        finally:
            shutil.rmtree(session_dir, ignore_errors=True)
    finally:
        shutil.rmtree(prev_session_dir, ignore_errors=True)
        if checkpoint_path.exists():
            checkpoint_path.unlink()


def test_setup_paths_creates_dirs_and_is_fluent(harvey: Harvey):
    result = harvey.setup_paths()
    assert result is harvey
    assert harvey.repos_dir.is_dir()
    assert harvey.docs_dir.is_dir()


def test_ingest_requires_cv_and_job(harvey: Harvey):
    with pytest.raises(FileNotFoundError):
        harvey.ingest_documents()

    (harvey.docs_dir / "cv.md").write_text("CV", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        harvey.ingest_documents()


def test_ingest_copies_cv_and_job_to_session(harvey: Harvey):
    _seed_required(harvey)
    harvey.ingest_documents()
    assert (harvey.session_docs_dir / "cv.md").read_text(encoding="utf-8") == "CV"
    assert (harvey.session_docs_dir / "job.md").read_text(encoding="utf-8") == "JOB"


def test_ingest_routes_background_to_anti_karen_when_blind(harvey: Harvey, monkeypatch):
    monkeypatch.setenv("KAREN_READS_BACKGROUND", "no")
    _seed_required(harvey)
    (harvey.docs_dir / "who_are_u.md").write_text("SECRET", encoding="utf-8")

    harvey.ingest_documents()

    assert (harvey.session_dir / "anti_karen" / "who_are_u.md").exists()
    assert not (harvey.session_docs_dir / "who_are_u.md").exists()


def test_ingest_keeps_background_in_docs_when_allowed(harvey: Harvey, monkeypatch):
    monkeypatch.setenv("KAREN_READS_BACKGROUND", "yes")
    _seed_required(harvey)
    (harvey.docs_dir / "who_are_u.md").write_text("OPEN", encoding="utf-8")

    harvey.ingest_documents()

    assert (harvey.session_docs_dir / "who_are_u.md").exists()
    assert not (harvey.session_dir / "anti_karen" / "who_are_u.md").exists()


def test_ingest_defaults_to_allowing_background(harvey: Harvey, monkeypatch):
    monkeypatch.delenv("KAREN_READS_BACKGROUND", raising=False)
    _seed_required(harvey)
    (harvey.docs_dir / "who_are_u.md").write_text("OPEN", encoding="utf-8")

    harvey.ingest_documents()

    assert (harvey.session_docs_dir / "who_are_u.md").exists()


def test_ingest_is_fluent(harvey: Harvey):
    _seed_required(harvey)
    assert harvey.ingest_documents() is harvey


def test_print_session_id_outputs_and_is_fluent(harvey: Harvey, capsys):
    harvey.session_id = "abc-123"
    result = harvey.print_session_id()
    assert result is harvey
    assert capsys.readouterr().out.strip() == "abc-123"
