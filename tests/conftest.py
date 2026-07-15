from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REAL_DATA_DIR = (REPOSITORY_ROOT / ".data").resolve()
TEST_ROOT = Path(tempfile.mkdtemp(prefix="meta-2028-pytest-"))
TEST_DATA_DIR = TEST_ROOT / "data"
TEST_RUNS_DIR = TEST_ROOT / "runs"
TEST_SESSION_ROOT = TEST_ROOT / "sessions"


def assert_safe_test_path(path: Path) -> None:
    resolved = path.resolve()
    if resolved == REAL_DATA_DIR or REAL_DATA_DIR in resolved.parents:
        raise pytest.UsageError(f"Refusing to run tests against real data: {resolved}")


for configured_path in (TEST_DATA_DIR, TEST_RUNS_DIR, TEST_SESSION_ROOT):
    assert_safe_test_path(configured_path)
    configured_path.mkdir(parents=True, exist_ok=True)

os.environ["PIPELINE_DATA_DIR"] = str(TEST_DATA_DIR)
os.environ["PIPELINE_RUNS_DIR"] = str(TEST_RUNS_DIR)
os.environ["PIPELINE_SESSION_ROOT"] = str(TEST_SESSION_ROOT)


@pytest.fixture(autouse=True)
def _guard_runtime_paths() -> None:
    for environment_name in (
        "PIPELINE_DATA_DIR",
        "PIPELINE_RUNS_DIR",
        "PIPELINE_SESSION_ROOT",
    ):
        assert_safe_test_path(Path(os.environ[environment_name]))
