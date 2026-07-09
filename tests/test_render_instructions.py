import json
import subprocess
import pytest
from pathlib import Path

def test_shadow_rendering_success(tmp_path):
    data_file = tmp_path / "shadow_data.json"
    data = {
        "session_id": "test-session-123",
        "session_dir": "/tmp/karen_guard_test-session-123"
    }
    data_file.write_text(json.dumps(data), encoding="utf-8")

    template_file = tmp_path / "shadow_template.md"
    template_file.write_text("Session: {{ session_id }} in dir {{ session_dir }} — unicode: áéíóú", encoding="utf-8")

    output_dir = tmp_path / "output"

    args = [
        "uv", "run", "python", "harvey_guy/render_instructions.py",
        "--agent", "shadow",
        "--data-file", str(data_file),
        "--template-path", str(template_file),
        "--output-dir", str(output_dir)
    ]

    res = subprocess.run(args, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Deterministic contract and prompt rendered successfully" in res.stdout

    # Check generated files
    assert (output_dir / "shadow_input.json").exists()
    assert (output_dir / "shadow_instructions.md").exists()
    assert (output_dir / "shadow.prompt").exists()

    # Validate content
    input_json = json.loads((output_dir / "shadow_input.json").read_text(encoding="utf-8"))
    assert input_json["session_id"] == "test-session-123"

    instructions = (output_dir / "shadow_instructions.md").read_text(encoding="utf-8")
    assert "Session: test-session-123 in dir /tmp/karen_guard_test-session-123 — unicode: áéíóú" in instructions

    prompt = (output_dir / "shadow.prompt").read_text(encoding="utf-8")
    assert "Welcome, Harvey Shadow!" in prompt
    assert str(output_dir / "shadow_instructions.md") in prompt

def test_bill_rendering_success(tmp_path):
    data_file = tmp_path / "bill_data.json"
    data = {
        "session_id": "test-session-123",
        "session_dir": "/tmp/karen_guard_test-session-123",
        "karen_report_path": "/tmp/karen_guard_test-session-123/anti_karen/karen_output.md",
        "candidate_background_path": None
    }
    data_file.write_text(json.dumps(data), encoding="utf-8")

    template_file = tmp_path / "bill_template.md"
    template_file.write_text("Report: {{ karen_report_path }} — bg: {{ candidate_background_path }}", encoding="utf-8")

    output_dir = tmp_path / "output"

    args = [
        "uv", "run", "python", "harvey_guy/render_instructions.py",
        "--agent", "bill",
        "--data-file", str(data_file),
        "--template-path", str(template_file),
        "--output-dir", str(output_dir)
    ]

    res = subprocess.run(args, capture_output=True, text=True)
    assert res.returncode == 0

    instructions = (output_dir / "bill_instructions.md").read_text(encoding="utf-8")
    assert "bg: None" in instructions or "bg: " in instructions

    # Test with non-None background
    data["candidate_background_path"] = "/tmp/who_are_u.md"
    data_file.write_text(json.dumps(data), encoding="utf-8")
    res = subprocess.run(args, capture_output=True, text=True)
    assert res.returncode == 0
    instructions = (output_dir / "bill_instructions.md").read_text(encoding="utf-8")
    assert "bg: /tmp/who_are_u.md" in instructions

def test_donna_rendering_success(tmp_path):
    data_file = tmp_path / "donna_data.json"
    data = {
        "session_id": "test-session-123",
        "session_dir": "/tmp/karen_guard_test-session-123",
        "karen_report_path": "/tmp/karen_guard_test-session-123/anti_karen/karen_output.md",
        "fit_score": 85,
        "min_fit_score": 80
    }
    data_file.write_text(json.dumps(data), encoding="utf-8")

    template_file = tmp_path / "donna_template.md"
    template_file.write_text("Score: {{ fit_score }}/100 (min: {{ min_fit_score }}/100)", encoding="utf-8")

    output_dir = tmp_path / "output"

    args = [
        "uv", "run", "python", "harvey_guy/render_instructions.py",
        "--agent", "donna",
        "--data-file", str(data_file),
        "--template-path", str(template_file),
        "--output-dir", str(output_dir)
    ]

    res = subprocess.run(args, capture_output=True, text=True)
    assert res.returncode == 0
    instructions = (output_dir / "donna_instructions.md").read_text(encoding="utf-8")
    assert "Score: 85/100 (min: 80/100)" in instructions

def test_validation_type_error(tmp_path):
    data_file = tmp_path / "donna_bad.json"
    data = {
        "session_id": "test-session-123",
        "session_dir": "/tmp/karen_guard_test-session-123",
        "karen_report_path": "/tmp/karen_guard_test-session-123/anti_karen/karen_output.md",
        "fit_score": "eighty-five",  # type error: should be int
        "min_fit_score": 80
    }
    data_file.write_text(json.dumps(data), encoding="utf-8")

    template_file = tmp_path / "donna_template.md"
    template_file.write_text("Score: {{ fit_score }}", encoding="utf-8")

    args = [
        "uv", "run", "python", "harvey_guy/render_instructions.py",
        "--agent", "donna",
        "--data-file", str(data_file),
        "--template-path", str(template_file),
        "--output-dir", str(tmp_path / "output")
    ]

    res = subprocess.run(args, capture_output=True, text=True)
    assert res.returncode != 0
    assert "Pydantic validation failed for donna" in res.stderr

def test_validation_missing_field(tmp_path):
    data_file = tmp_path / "shadow_bad.json"
    data = {
        "session_id": "test-session-123"
        # session_dir missing
    }
    data_file.write_text(json.dumps(data), encoding="utf-8")

    template_file = tmp_path / "shadow_template.md"
    template_file.write_text("Hello", encoding="utf-8")

    args = [
        "uv", "run", "python", "harvey_guy/render_instructions.py",
        "--agent", "shadow",
        "--data-file", str(data_file),
        "--template-path", str(template_file),
        "--output-dir", str(tmp_path / "output")
    ]

    res = subprocess.run(args, capture_output=True, text=True)
    assert res.returncode != 0
    assert "Pydantic validation failed for shadow" in res.stderr

def test_invalid_agent_choice():
    args = [
        "uv", "run", "python", "harvey_guy/render_instructions.py",
        "--agent", "invalid_agent",
        "--data-file", "some_file.json",
        "--template-path", "some_template.md",
        "--output-dir", "/tmp"
    ]
    res = subprocess.run(args, capture_output=True, text=True)
    assert res.returncode != 0
    assert "invalid choice" in res.stderr
