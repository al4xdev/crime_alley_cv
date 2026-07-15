from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from harvey_guy.harvey_guy import Harvey


def _seed_documents(data_dir: Path, *, include_background: bool = True) -> None:
    docs = data_dir / "docs"
    docs.mkdir(parents=True)
    (docs / "cv.md").write_text("A sufficiently detailed CV", encoding="utf-8")
    (docs / "job.md").write_text("# Engineer — Acme\nDetails", encoding="utf-8")
    if include_background:
        (docs / "who_are_u.md").write_text("# Private background", encoding="utf-8")
    (docs / "action_plan.md").write_text("# Stale output", encoding="utf-8")


def test_session_is_fresh_and_ingests_only_canonical_inputs(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    session_root = tmp_path / "sessions"
    _seed_documents(data_dir)

    harvey = Harvey.setup(
        data_dir=data_dir,
        session_root=session_root,
        karen_reads_background=False,
    )
    harvey.setup_paths().ingest_documents()

    assert uuid.UUID(harvey.session_id)
    assert harvey.session_dir.parent == session_root
    assert {path.name for path in (harvey.session_dir / "docs").iterdir()} == {
        "cv.md",
        "job.md",
    }
    assert (harvey.session_dir / "anti_karen" / "artifacts" / "who_are_u.md").is_file()
    assert not (harvey.session_dir / "docs" / "action_plan.md").exists()


def test_background_can_be_routed_to_karen(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _seed_documents(data_dir)
    harvey = Harvey.setup(
        data_dir=data_dir,
        session_root=tmp_path / "sessions",
        karen_reads_background=True,
    )
    harvey.setup_paths().ingest_documents()
    assert (harvey.session_dir / "docs" / "who_are_u.md").is_file()
    assert not (harvey.session_dir / "anti_karen" / "artifacts" / "who_are_u.md").exists()


def test_missing_required_document_fails(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    (data_dir / "docs").mkdir(parents=True)
    harvey = Harvey.setup(data_dir=data_dir, session_root=tmp_path / "sessions")
    harvey.setup_paths()
    with pytest.raises(FileNotFoundError):
        harvey.ingest_documents()


def test_invalid_background_setting_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAREN_READS_BACKGROUND", "maybe")
    with pytest.raises(ValueError, match="must be 'yes' or 'no'"):
        Harvey()
