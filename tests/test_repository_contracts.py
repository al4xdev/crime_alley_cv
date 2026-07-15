from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINNED_ACTION = re.compile(r"uses: [^\s@]+@[0-9a-f]{40}(?:\s+#\s+\S+)?$")


def _text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_runbooks_follow_configurable_data_and_canonical_commands() -> None:
    harvey = _text("harvey_guy/main.md")
    donna = _text("donna_nana/main.md")
    karen = _text("karen_guard/main.md")

    assert ".data/docs" not in harvey
    assert ".data/docs" not in donna
    assert "{{ action_plan_path }}" in donna
    assert "karen_run.err" not in karen
    assert "uv run python -m harvey_guy.pipeline record-evaluation" in karen


def test_ci_uses_frozen_environment_and_pinned_actions() -> None:
    ci = _text(".github/workflows/ci.yml")
    action_lines = [
        line.strip()
        for line in ci.splitlines()
        if line.strip().startswith("uses:")
    ]

    assert action_lines
    assert all(PINNED_ACTION.fullmatch(line) for line in action_lines)
    assert not (ROOT / ".github" / "workflows" / "publish.yml").exists()
    assert "tags: ['v*.*.*']" in ci
    assert "uv sync --frozen --group dev" in ci
    assert "docker build --file karen_guard/Dockerfile" in ci
    assert "docker build --tag crime_alley_pipeline:ci" in ci
    assert "needs: [check, container-builds]" in ci
    assert "github.event_name == 'push'" in ci
    assert "packages: write" in ci
    assert "provenance: mode=max" in ci
    assert "sbom: true" in ci


def test_removed_duplicate_layout_boundary_stays_removed() -> None:
    assert not (ROOT / "boundaries" / "layout.fish").exists()
