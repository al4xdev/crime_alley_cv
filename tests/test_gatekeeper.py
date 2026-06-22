from __future__ import annotations

from pathlib import Path

import pytest

from harvey_guy.gatekeeper import extract_score, main


def test_extract_score_various_formats():
    # Standard format
    assert extract_score("## Technical Fit Score: 78/100\nSome other text") == 78

    # Detailed bold markdown
    assert extract_score("- **Technical Fit Score (0 to 100)**: **82/100**") == 82

    # Score on a line by itself
    assert extract_score("Score: 90/100") == 90

    # Score with space and bold
    assert extract_score("- **Score**: **65/100**") == 65

    # Raw slash format
    assert extract_score("Final evaluation score is 88/100.") == 88

    # No score raises ValueError
    with pytest.raises(ValueError, match="Could not extract a valid fit score"):
        extract_score("The candidate has some skills but no score is specified.")


def test_gatekeeper_main_missing_session(tmp_path: Path, monkeypatch):
    args = [
        "gatekeeper.py",
        "--min-fit-score",
        "80",
        "--max-loops",
        "3",
        "--current-loop",
        "0",
        "--session-dir",
        str(tmp_path / "nonexistent"),
    ]
    monkeypatch.setattr("sys.argv", args)

    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 3


def test_gatekeeper_main_missing_report(tmp_path: Path, monkeypatch):
    session_dir = tmp_path / "karen_guard_session"
    session_dir.mkdir()

    args = [
        "gatekeeper.py",
        "--min-fit-score",
        "80",
        "--max-loops",
        "3",
        "--current-loop",
        "0",
        "--session-dir",
        str(session_dir),
    ]
    monkeypatch.setattr("sys.argv", args)

    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 3


def test_gatekeeper_main_success_flow(tmp_path: Path, monkeypatch, capsys):
    session_dir = tmp_path / "karen_guard_session"
    session_dir.mkdir()

    # Create CV inside session docs
    docs_dir = session_dir / "docs"
    docs_dir.mkdir()
    src_cv = docs_dir / "cv.md"
    src_cv.write_text("Optimized CV", encoding="utf-8")

    # Create Karen report in anti_karen
    anti_karen = session_dir / "anti_karen"
    anti_karen.mkdir()
    karen_report = anti_karen / "karen_output.md"
    karen_report.write_text("## Technical Fit Score: 85/100", encoding="utf-8")

    # Target data docs
    data_dir = tmp_path / "data" / "docs"

    args = [
        "gatekeeper.py",
        "--min-fit-score",
        "80",
        "--max-loops",
        "3",
        "--current-loop",
        "0",
        "--session-dir",
        str(session_dir),
        "--karen-report",
        str(karen_report),
        "--data-dir",
        str(data_dir),
    ]
    monkeypatch.setattr("sys.argv", args)

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0

    # Verify final CV copied
    dest_cv = data_dir / "cv.md"
    assert dest_cv.exists()
    assert dest_cv.read_text(encoding="utf-8") == "Optimized CV"

    # Verify printed JSON status
    captured = capsys.readouterr()
    assert '"status": "success"' in captured.out
    assert '"fit_score": 85' in captured.out


def test_gatekeeper_main_max_loops_flow(tmp_path: Path, monkeypatch, capsys):
    session_dir = tmp_path / "karen_guard_session"
    session_dir.mkdir()

    docs_dir = session_dir / "docs"
    docs_dir.mkdir()
    src_cv = docs_dir / "cv.md"
    src_cv.write_text("CV at Max Loops", encoding="utf-8")

    anti_karen = session_dir / "anti_karen"
    anti_karen.mkdir()
    karen_report = anti_karen / "karen_output.md"
    karen_report.write_text("## Technical Fit Score: 72/100", encoding="utf-8")

    data_dir = tmp_path / "data" / "docs"

    args = [
        "gatekeeper.py",
        "--min-fit-score",
        "80",
        "--max-loops",
        "3",
        "--current-loop",
        "3",  # current loop meets limit (3 >= 3)
        "--session-dir",
        str(session_dir),
        "--karen-report",
        str(karen_report),
        "--data-dir",
        str(data_dir),
    ]
    monkeypatch.setattr("sys.argv", args)

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1

    # Verify CV copied
    dest_cv = data_dir / "cv.md"
    assert dest_cv.exists()
    assert dest_cv.read_text(encoding="utf-8") == "CV at Max Loops"

    # Verify printed JSON status
    captured = capsys.readouterr()
    assert '"status": "max_loops"' in captured.out
    assert '"fit_score": 72' in captured.out


def test_gatekeeper_main_continue_flow(tmp_path: Path, monkeypatch, capsys):
    session_dir = tmp_path / "karen_guard_session"
    session_dir.mkdir()

    docs_dir = session_dir / "docs"
    docs_dir.mkdir()

    anti_karen = session_dir / "anti_karen"
    anti_karen.mkdir()
    karen_report = anti_karen / "karen_output.md"
    karen_report.write_text("## Technical Fit Score: 75/100", encoding="utf-8")

    data_dir = tmp_path / "data" / "docs"

    args = [
        "gatekeeper.py",
        "--min-fit-score",
        "80",
        "--max-loops",
        "3",
        "--current-loop",
        "1",  # loop 1 < limit 3
        "--session-dir",
        str(session_dir),
        "--karen-report",
        str(karen_report),
        "--data-dir",
        str(data_dir),
    ]
    monkeypatch.setattr("sys.argv", args)

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 2

    # Verify CV NOT copied (since we're continuing the loop)
    dest_cv = data_dir / "cv.md"
    assert not dest_cv.exists()

    # Verify printed JSON status
    captured = capsys.readouterr()
    assert '"status": "continue"' in captured.out
    assert '"fit_score": 75' in captured.out
