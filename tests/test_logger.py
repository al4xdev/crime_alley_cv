from __future__ import annotations

from pathlib import Path

from harvey_guy.libs import Log


def test_config_starts_at_zero(tmp_path: Path):
    log = Log.config(tmp_path / "a.log", tool="logtest-config")
    assert isinstance(log, Log)
    assert log._count == 0


def test_info_is_fluent_and_increments(tmp_path: Path):
    log = Log.config(tmp_path / "b.log", tool="logtest-incr")
    assert log.info("hello") is log
    assert log._count == 1
    log.info("again")
    assert log._count == 2


def test_counter_prefix_is_written(tmp_path: Path):
    path = tmp_path / "c.log"
    Log.config(path, tool="logtest-prefix").info("first").info("second")
    content = path.read_text(encoding="utf-8")
    assert "[1] first" in content
    assert "[2] second" in content


def test_levels_chain_and_share_counter(tmp_path: Path):
    log = Log.config(tmp_path / "d.log", tool="logtest-levels")
    log.warning("w").error("e")
    assert log._count == 2
