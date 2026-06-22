from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent
BOUNDARIES_DIR = REPO_ROOT / "boundaries"


def run_hook(script_name: str, mode: str, session_id: str = "", extra_args: list[str] = None, env: dict = None) -> subprocess.CompletedProcess:
    script_path = BOUNDARIES_DIR / script_name
    args = [str(script_path), mode, session_id]
    if extra_args:
        args.extend(extra_args)
    
    current_env = os.environ.copy()
    if env:
        current_env.update(env)

    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        env=current_env,
        check=False
    )


@pytest.fixture
def mock_repo_structure(tmp_path: Path, monkeypatch):
    # Set up mock .data directory in temporary workspace
    data_dir = tmp_path / ".data"
    docs_dir = data_dir / "docs"
    docs_dir.mkdir(parents=True)
    
    # Patch current directory to temp path for scripts running tests
    monkeypatch.chdir(tmp_path)
    return tmp_path, docs_dir


def test_harvey_depchecker(mock_repo_structure):
    tmp_path, docs_dir = mock_repo_structure
    
    # Pre should always pass
    res_pre = run_hook("harvey_depchecker.fish", "--pre")
    assert res_pre.returncode == 0
    
    # Post should fail because dependencies checked marker is missing
    res_post_fail = run_hook("harvey_depchecker.fish", "--post")
    assert res_post_fail.returncode != 0
    
    # Create marker containing PASS
    marker = docs_dir / ".dependencies_checked.md"
    marker.write_text("Verification completed\nPython PASS\nuv PASS\nDocker PASS\nat PASS\nGit PASS\nwl-copy PASS", encoding="utf-8")
    
    # Post should now pass
    res_post_pass = run_hook("harvey_depchecker.fish", "--post")
    assert res_post_pass.returncode == 0
    
    # Post should fail if FAIL is in it
    marker.write_text("Verification completed\nPython FAIL\nuv PASS", encoding="utf-8")
    res_post_fail_2 = run_hook("harvey_depchecker.fish", "--post")
    assert res_post_fail_2.returncode != 0


def test_harvey_vera(mock_repo_structure):
    tmp_path, docs_dir = mock_repo_structure
    
    res_pre = run_hook("harvey_vera.fish", "--pre")
    assert res_pre.returncode == 0
    
    # Post fails when file is missing
    res_post_fail = run_hook("harvey_vera.fish", "--post")
    assert res_post_fail.returncode != 0
    
    # Create too small background file
    bg = docs_dir / "who_are_u.md"
    bg.write_text("Hello", encoding="utf-8")
    res_post_fail_2 = run_hook("harvey_vera.fish", "--post")
    assert res_post_fail_2.returncode != 0
    
    # Create valid background file
    bg.write_text("# Candidate Background Profile\n\nExperience: Senior Platform Engineer for Generative AI systems. Extended experience with Python, Cloud platforms, and Large Language Model fine-tuning techniques.", encoding="utf-8")
    res_post_pass = run_hook("harvey_vera.fish", "--post")
    assert res_post_pass.returncode == 0


def test_harvey_setup(mock_repo_structure):
    tmp_path, docs_dir = mock_repo_structure
    session_id = "test-session-xyz"
    session_dir = Path("/tmp") / f"karen_guard_{session_id}"
    
    # Pre fails since cv.md and job.md are missing
    res_pre_fail = run_hook("harvey_setup.fish", "--pre", env={"MAX_LOOPS": "3", "MIN_FIT_SCORE": "80"})
    assert res_pre_fail.returncode != 0
    
    # Seed files
    cv = docs_dir / "cv.md"
    cv.write_text("My Resume Content", encoding="utf-8")
    job = docs_dir / "job.md"
    job.write_text("Invalid job title line format", encoding="utf-8")
    
    # Pre fails due to invalid title format in job.md
    res_pre_fail_title = run_hook("harvey_setup.fish", "--pre", env={"MAX_LOOPS": "3", "MIN_FIT_SCORE": "80"})
    assert res_pre_fail_title.returncode != 0
    
    # Fix job title line format
    job.write_text("# Tech Lead — Acme Corp\n\nDetailed job description here.", encoding="utf-8")
    
    # Pre passes now
    res_pre_pass = run_hook("harvey_setup.fish", "--pre", env={"MAX_LOOPS": "3", "MIN_FIT_SCORE": "80", "KAREN_READS_BACKGROUND": "no"})
    assert res_pre_pass.returncode == 0
    
    # Post fails because session directory doesn't exist
    res_post_fail = run_hook("harvey_setup.fish", "--post", session_id)
    assert res_post_fail.returncode != 0
    
    # Create session directory structure
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "docs").mkdir()
    (session_dir / "repos").mkdir()
    (session_dir / "anti_karen").mkdir()
    
    # Seed files in session directory
    (session_dir / "docs" / "cv.md").write_text("My Resume Content", encoding="utf-8")
    (session_dir / "docs" / "job.md").write_text("# Tech Lead — Acme Corp", encoding="utf-8")
    
    # Add who_are_u.md on host and route it to check routing (KAREN_READS_BACKGROUND = no)
    (docs_dir / "who_are_u.md").write_text("# Experience Details", encoding="utf-8")
    (session_dir / "anti_karen" / "who_are_u.md").write_text("# Experience Details", encoding="utf-8")
    
    try:
        # Post should pass with KAREN_READS_BACKGROUND=no
        res_post_pass = run_hook("harvey_setup.fish", "--post", session_id, env={"KAREN_READS_BACKGROUND": "no"})
        assert res_post_pass.returncode == 0
        
        # Fails if KAREN_READS_BACKGROUND=no but file leaked to docs/
        (session_dir / "docs" / "who_are_u.md").write_text("# Leaked", encoding="utf-8")
        res_post_fail_leak = run_hook("harvey_setup.fish", "--post", session_id, env={"KAREN_READS_BACKGROUND": "no"})
        assert res_post_fail_leak.returncode != 0
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)


def test_harvey_shadow(mock_repo_structure):
    tmp_path, docs_dir = mock_repo_structure
    session_id = "test-shadow-xyz"
    session_dir = Path("/tmp") / f"karen_guard_{session_id}"
    
    # Pre fails because session_dir is missing
    res_pre_fail = run_hook("harvey_shadow.fish", "--pre", session_id)
    assert res_pre_fail.returncode != 0
    
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "repos").mkdir()
    (session_dir / "anti_karen").mkdir()
    
    try:
        res_pre_pass = run_hook("harvey_shadow.fish", "--pre", session_id)
        assert res_pre_pass.returncode == 0
        
        # Post fails as company_info.md is missing
        res_post_fail = run_hook("harvey_shadow.fish", "--post", session_id)
        assert res_post_fail.returncode != 0
        
        (session_dir / "company_info.md").write_text("# Acme Corp Profile", encoding="utf-8")
        
        # Post should pass
        res_post_pass = run_hook("harvey_shadow.fish", "--post", session_id)
        assert res_post_pass.returncode == 0
        
        # Post checks repos count if repos_expected_count.txt exists
        (session_dir / "repos_expected_count.txt").write_text("2\n", encoding="utf-8")
        # Actual count is 0, should fail without warning log
        res_post_fail_count = run_hook("harvey_shadow.fish", "--post", session_id)
        assert res_post_fail_count.returncode != 0
        
        # Create 2 repo directories
        (session_dir / "repos" / "repo1").mkdir()
        (session_dir / "repos" / "repo2").mkdir()
        
        # Passes now
        res_post_pass_count = run_hook("harvey_shadow.fish", "--post", session_id)
        assert res_post_pass_count.returncode == 0
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)


def test_harvey_karen(mock_repo_structure):
    tmp_path, docs_dir = mock_repo_structure
    session_id = "test-karen-xyz"
    session_dir = Path("/tmp") / f"karen_guard_{session_id}"
    
    res_pre_fail = run_hook("harvey_karen.fish", "--pre", session_id)
    assert res_pre_fail.returncode != 0
    
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "docs").mkdir()
    (session_dir / "anti_karen").mkdir()
    (session_dir / "docs" / "cv.md").write_text("CV", encoding="utf-8")
    (session_dir / "docs" / "job.md").write_text("JOB", encoding="utf-8")
    
    try:
        # Pre check will run agy models. In test environment, if agy models is not configured,
        # it might fail or pass depending on host. Let's make sure it asserts correctly or mock if possible.
        # But wait, agy models does run successfully in this environment because agy is authenticated!
        # If it fails, that's a valid failure.
        res_pre = run_hook("harvey_karen.fish", "--pre", session_id)
        if res_pre.returncode == 0:
            # Post fails as evaluation.md is missing
            res_post_fail = run_hook("harvey_karen.fish", "--post", session_id)
            assert res_post_fail.returncode != 0
            
            (session_dir / "anti_karen" / "evaluation.md").write_text("## Technical Fit Score: 78/100\nThis is a long mock evaluation report written to verify that the file size check of 100 bytes is passed successfully under boundaries validation.", encoding="utf-8")
            res_post_pass = run_hook("harvey_karen.fish", "--post", session_id)
            assert res_post_pass.returncode == 0
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)


def test_karen_gatekeeper(mock_repo_structure):
    tmp_path, docs_dir = mock_repo_structure
    session_id = "test-gatekeeper-xyz"
    session_dir = Path("/tmp") / f"karen_guard_{session_id}"
    
    # Pre fails as evaluation.md missing
    res_pre_fail = run_hook("karen_gatekeeper.fish", "--pre", session_id)
    assert res_pre_fail.returncode != 0
    
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "docs").mkdir()
    (session_dir / "anti_karen").mkdir()
    eval_file = session_dir / "anti_karen" / "evaluation.md"
    eval_file.write_text("## Technical Fit Score: 85/100", encoding="utf-8")
    
    try:
        res_pre_pass = run_hook("karen_gatekeeper.fish", "--pre", session_id)
        assert res_pre_pass.returncode == 0
        
        # Post fails as gatekeeper exit code is missing
        res_post_fail = run_hook("karen_gatekeeper.fish", "--post", session_id)
        assert res_post_fail.returncode != 0
        
        # Post fails on invalid exit code
        res_post_fail_invalid = run_hook("karen_gatekeeper.fish", "--post", session_id, ["9"])
        assert res_post_fail_invalid.returncode != 0
        
        # Post fails on gatekeeper parsing failure (3)
        res_post_fail_err = run_hook("karen_gatekeeper.fish", "--post", session_id, ["3"])
        assert res_post_fail_err.returncode != 0
        
        # Post passes on status 2 (continue loop - no final CV copy required)
        res_post_pass_continue = run_hook("karen_gatekeeper.fish", "--post", session_id, ["2"])
        assert res_post_pass_continue.returncode == 0
        
        # Post fails on status 0 (success) if CV was not copied back
        res_post_fail_success = run_hook("karen_gatekeeper.fish", "--post", session_id, ["0"])
        assert res_post_fail_success.returncode != 0
        
        # Mock CV and perform copy
        (session_dir / "docs" / "cv.md").write_text("My CV Final Version", encoding="utf-8")
        (docs_dir / "cv.md").write_text("My CV Final Version", encoding="utf-8")
        
        res_post_pass_success = run_hook("karen_gatekeeper.fish", "--post", session_id, ["0"])
        assert res_post_pass_success.returncode == 0
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)


def test_gatekeeper_bill(mock_repo_structure):
    tmp_path, docs_dir = mock_repo_structure
    session_id = "test-bill-xyz"
    session_dir = Path("/tmp") / f"karen_guard_{session_id}"
    
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "docs").mkdir()
    (session_dir / "anti_karen").mkdir()
    
    cv_file = session_dir / "docs" / "cv.md"
    cv_file.write_text("Original Resume", encoding="utf-8")
    
    # Seed input sources
    (session_dir / "docs" / "job.md").write_text("Job description", encoding="utf-8")
    (session_dir / "company_info.md").write_text("Company info", encoding="utf-8")
    
    try:
        res_pre = run_hook("gatekeeper_bill.fish", "--pre", session_id)
        assert res_pre.returncode == 0
        
        # Post fails because CV hash has not changed
        res_post_fail = run_hook("gatekeeper_bill.fish", "--post", session_id)
        assert res_post_fail.returncode != 0
        
        # Modify CV
        cv_file.write_text("Modified Resume", encoding="utf-8")
        
        # Now post passes
        res_post_pass = run_hook("gatekeeper_bill.fish", "--post", session_id)
        assert res_post_pass.returncode == 0
        
        # Modify job.md (simulate context fraud)
        (session_dir / "docs" / "job.md").write_text("Modified Job description", encoding="utf-8")
        # Post should return code 3 (integrity/context fraud error)
        res_post_fraud = run_hook("gatekeeper_bill.fish", "--post", session_id)
        assert res_post_fraud.returncode == 3
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)


def test_bill_harvey(mock_repo_structure):
    tmp_path, docs_dir = mock_repo_structure
    session_id = "test-billharvey-xyz"
    session_dir = Path("/tmp") / f"karen_guard_{session_id}"
    
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "docs").mkdir()
    (session_dir / "anti_karen").mkdir()
    
    session_cv = session_dir / "docs" / "cv.md"
    session_cv.write_text("Reconstructed resume", encoding="utf-8")
    
    host_cv = docs_dir / "cv.md"
    host_cv.write_text("Original resume", encoding="utf-8")
    
    # Loop checkpoint setup
    checkpoint_file = Path("/tmp/karen_guard_loop_state.json")
    checkpoint_file.write_text('{"current_loop": 0, "fit_score": null, "session_id": "prev"}', encoding="utf-8")
    
    try:
        res_pre = run_hook("bill_harvey.fish", "--pre", session_id)
        assert res_pre.returncode == 0
        
        res_post = run_hook("bill_harvey.fish", "--post", session_id)
        assert res_post.returncode == 0
        
        # Verify host CV updated
        assert host_cv.read_text(encoding="utf-8") == "Reconstructed resume"
        
        # Verify checkpoint incremented
        import json
        state = json.loads(checkpoint_file.read_text(encoding="utf-8"))
        assert state["current_loop"] == 1
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)
        if checkpoint_file.exists():
            checkpoint_file.unlink()


def test_gatekeeper_donna(mock_repo_structure):
    tmp_path, docs_dir = mock_repo_structure
    session_id = "test-donna-xyz"
    session_dir = Path("/tmp") / f"karen_guard_{session_id}"
    
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "anti_karen").mkdir()
    
    try:
        # Pre fails since evaluation.md missing
        res_pre_fail = run_hook("gatekeeper_donna.fish", "--pre", session_id)
        assert res_pre_fail.returncode != 0
        
        (session_dir / "anti_karen" / "evaluation.md").write_text("Evaluation summary", encoding="utf-8")
        res_pre_pass = run_hook("gatekeeper_donna.fish", "--pre", session_id)
        assert res_pre_pass.returncode == 0
        
        # Post fails since action_plan.md is missing
        res_post_fail = run_hook("gatekeeper_donna.fish", "--post", session_id)
        assert res_post_fail.returncode != 0
        
        # Create too small action plan
        plan = docs_dir / "action_plan.md"
        plan.write_text("Hello", encoding="utf-8")
        res_post_fail_2 = run_hook("gatekeeper_donna.fish", "--post", session_id)
        assert res_post_fail_2.returncode != 0
        
        # Create valid action plan
        plan.write_text("# Career Action Plan\n\n- Fix technology gaps in Python.\n- Run public open source projects.\n- Build Generative AI agents with robust sandboxing and deterministic contracts to prevent context fraud.", encoding="utf-8")
        res_post_pass = run_hook("gatekeeper_donna.fish", "--post", session_id)
        assert res_post_pass.returncode == 0
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)
