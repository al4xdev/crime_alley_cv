from __future__ import annotations

import os
import subprocess
import shutil
import tempfile
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent
RUN_SH = REPO_ROOT / "karen_guard" / "run.sh"

@pytest.fixture
def temp_home_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)

@pytest.fixture
def tmp_session():
    session_id = "test-session-id-12345"
    session_dir = Path("/tmp") / f"karen_guard_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    # create required files
    (session_dir / "company_info.md").write_text("# Company Info", encoding="utf-8")
    yield session_id, session_dir
    shutil.rmtree(session_dir, ignore_errors=True)

def test_run_sh_auth_success(tmp_session, temp_home_dir, monkeypatch):
    session_id, session_dir = tmp_session

    # Create mock bin directory for podman
    mock_bin_dir = temp_home_dir / "bin"
    mock_bin_dir.mkdir()
    mock_podman = mock_bin_dir / "podman"
    
    # Write mock podman that:
    # 1. On "podman image exists", exits 0.
    # 2. On "agy models", prints Gemini models and exits 0.
    # 3. On "run_evaluator", writes evaluation.md to session out and exits 0.
    mock_podman.write_text(
        "#!/bin/sh\n"
        "if echo \"$@\" | grep -q \"image exists\"; then\n"
        "  exit 0\n"
        "elif echo \"$@\" | grep -q \"agy models\"; then\n"
        "  echo 'Gemini 3.5 Flash (Medium)'\n"
        "  exit 0\n"
        "elif echo \"$@\" | grep -q \"run_evaluator\"; then\n"
        "  mkdir -p " + str(session_dir) + "/out\n"
        "  echo 'Evaluation output' > " + str(session_dir) + "/out/evaluation.md\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8"
    )
    mock_podman.chmod(0o755)

    # Set up environments
    monkeypatch.setenv("PATH", f"{mock_bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("HOME", str(temp_home_dir))
    
    # Prepare dummy .gemini folder in temp home
    (temp_home_dir / ".gemini").mkdir()

    # Run the script
    proc = subprocess.run(
        [str(RUN_SH), session_id],
        capture_output=True,
        text=True,
        check=False
    )
    
    # Verify that the script succeeded
    assert proc.returncode == 0
    # Verify that it did NOT trigger interactive login flow
    assert "Starting interactive login flow" not in proc.stderr
    # Verify that evaluation.md was generated/moved correctly
    assert (session_dir / "anti_karen" / "evaluation.md").exists()

def test_run_sh_auth_false_positive_reproduces_bug(tmp_session, temp_home_dir, monkeypatch):
    """
    Regression test: This reproduces the bug where success/status messages containing
    the word 'Authentication' (e.g., 'Authentication check succeeded') trigger a false
    positive regex match, causing the script to think it is not authenticated and
    enter the interactive login flow.
    
    TODO: Once TASK-05 is implemented, this test should be updated to assert that
    'Starting interactive login flow' is NOT in proc.stderr.
    """
    session_id, session_dir = tmp_session

    # Create mock bin directory for podman
    mock_bin_dir = temp_home_dir / "bin"
    mock_bin_dir.mkdir()
    mock_podman = mock_bin_dir / "podman"
    
    # Write mock podman that outputs 'Authentication check succeeded' on agy models
    mock_podman.write_text(
        "#!/bin/sh\n"
        "if echo \"$@\" | grep -q \"image exists\"; then\n"
        "  exit 0\n"
        "elif echo \"$@\" | grep -q \"agy models\"; then\n"
        "  echo 'Authentication check succeeded. Models loaded.'\n"
        "  exit 0\n"
        "elif echo \"$@\" | grep -q \"run_evaluator\"; then\n"
        "  mkdir -p " + str(session_dir) + "/out\n"
        "  echo 'Evaluation output' > " + str(session_dir) + "/out/evaluation.md\n"
        "  exit 0\n"
        "elif echo \"$@\" | grep -q \"agy\"; then\n"
        "  # Simulate login by creating the token in session dir\n"
        "  mkdir -p " + str(session_dir) + "/.gemini/antigravity-cli\n"
        "  echo 'mock-oauth-token' > " + str(session_dir) + "/.gemini/antigravity-cli/antigravity-oauth-token\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8"
    )
    mock_podman.chmod(0o755)

    # Set up environments
    monkeypatch.setenv("PATH", f"{mock_bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("HOME", str(temp_home_dir))
    
    # Prepare dummy .gemini folder in temp home
    (temp_home_dir / ".gemini").mkdir()

    # Run the script
    proc = subprocess.run(
        [str(RUN_SH), session_id],
        capture_output=True,
        text=True,
        check=False
    )
    
    # Verify that the success check does not trigger interactive login flow
    assert "Starting interactive login flow" not in proc.stderr
    assert proc.returncode == 0



def test_run_sh_auth_needs_login(tmp_session, temp_home_dir, monkeypatch):
    session_id, session_dir = tmp_session

    # Create mock bin directory for podman
    mock_bin_dir = temp_home_dir / "bin"
    mock_bin_dir.mkdir()
    mock_podman = mock_bin_dir / "podman"
    
    # Write mock podman that:
    # 1. On "image exists", exits 0.
    # 2. On "agy models", exits 1 (needs authentication).
    # 3. On interactive login "agy", creates the auth file in session_gemini_dir to mock successful login.
    # 4. On "run_evaluator", writes evaluation.md to session out.
    mock_podman.write_text(
        "#!/bin/sh\n"
        "if echo \"$@\" | grep -q \"image exists\"; then\n"
        "  exit 0\n"
        "elif echo \"$@\" | grep -q \"agy models\"; then\n"
        "  echo 'Error: not signed in' >&2\n"
        "  exit 1\n"
        "elif echo \"$@\" | grep -q \"run_evaluator\"; then\n"
        "  mkdir -p " + str(session_dir) + "/out\n"
        "  echo 'Evaluation output' > " + str(session_dir) + "/out/evaluation.md\n"
        "  exit 0\n"
        "elif echo \"$@\" | grep -q \"agy\"; then\n"
        "  # This is the interactive login call. Simulate login by creating the token in session dir\n"
        "  mkdir -p " + str(session_dir) + "/.gemini/antigravity-cli\n"
        "  echo 'mock-oauth-token' > " + str(session_dir) + "/.gemini/antigravity-cli/antigravity-oauth-token\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8"
    )
    mock_podman.chmod(0o755)

    # Set up environments
    monkeypatch.setenv("PATH", f"{mock_bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("HOME", str(temp_home_dir))
    
    # Prepare dummy .gemini folder in temp home
    (temp_home_dir / ".gemini").mkdir()

    # Run the script
    proc = subprocess.run(
        [str(RUN_SH), session_id],
        capture_output=True,
        text=True,
        check=False
    )
    
    # Verify that the script succeeded
    assert proc.returncode == 0
    # Verify that it triggered interactive login flow
    assert "Starting interactive login flow" in proc.stderr
    # Verify that evaluation.md was generated/moved correctly
    assert (session_dir / "anti_karen" / "evaluation.md").exists()
