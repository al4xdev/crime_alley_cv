from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import UndefinedError
from pydantic import ValidationError

from harvey_guy.render_instructions import render_agent


def test_render_writes_validated_contract_and_prompt(tmp_path: Path) -> None:
    template = tmp_path / "shadow.md"
    template.write_text("Session {{ session_id }} at {{ session_dir }}\n", encoding="utf-8")
    rendered = render_agent(
        "shadow",
        {"session_id": "session-1", "session_dir": "/tmp/session-1"},
        template,
        tmp_path / "output",
    )

    assert rendered.input_json.is_file()
    assert rendered.instructions.read_text(encoding="utf-8") == (
        "Session session-1 at /tmp/session-1\n"
    )
    assert "Validated JSON:" in rendered.prompt.read_text(encoding="utf-8")


def test_unknown_template_variable_fails_loudly(tmp_path: Path) -> None:
    template = tmp_path / "shadow.md"
    template.write_text("{{ missing_contract_field }}", encoding="utf-8")
    with pytest.raises(UndefinedError):
        render_agent(
            "shadow",
            {"session_id": "session-1", "session_dir": "/tmp/session-1"},
            template,
            tmp_path / "output",
        )


def test_extra_or_wrongly_typed_contract_fields_are_rejected(tmp_path: Path) -> None:
    template = tmp_path / "donna.md"
    template.write_text("{{ fit_score }}", encoding="utf-8")
    with pytest.raises(ValidationError):
        render_agent(
            "donna",
            {
                "session_id": "session-1",
                "session_dir": "/tmp/session-1",
                "karen_report_path": "/tmp/report.md",
                "action_plan_path": "/tmp/action-plan.md",
                "fit_score": "85",
                "min_fit_score": 80,
                "legacy_field": True,
            },
            template,
            tmp_path / "output",
        )
