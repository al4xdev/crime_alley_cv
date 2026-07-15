from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RUN_SH = REPOSITORY_ROOT / "karen_guard" / "run.sh"


def _session(tmp_path: Path) -> Path:
    session = tmp_path / "karen_guard_test-session"
    for directory in ("docs", "repos", "out", "anti_karen"):
        (session / directory).mkdir(parents=True, exist_ok=True)
    (session / "company_info.md").write_text("# Company\n", encoding="utf-8")
    return session


def _home_with_token(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    token = home / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"
    token.parent.mkdir(parents=True)
    token.write_text("mock-oauth-token\n", encoding="utf-8")
    token.chmod(0o600)
    return home


def _mock_podman(
    tmp_path: Path,
    session: Path,
    *,
    auth_succeeds: bool,
) -> tuple[Path, Path]:
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    log = tmp_path / "podman.log"
    podman = binary_dir / "podman"
    auth_status = "0" if auth_succeeds else "1"
    podman.write_text(
        "#!/bin/sh\n"
        'printf \'%s\\n\' "$*" >> "$MOCK_PODMAN_LOG"\n'
        'if [ "$1" = "build" ]; then exit 0; fi\n'
        'if echo "$*" | grep -q "agy models"; then exit '
        + auth_status
        + "; fi\n"
        'if echo "$*" | grep -q "run_evaluator"; then\n'
        f"  printf 'Evaluation output\\n' > '{session}/out/evaluation.md'\n"
        "  exit 0\n"
        "fi\n"
        'if echo "$*" | grep -q "karen_guard agy"; then\n'
        f"  mkdir -p '{session}/.gemini/antigravity-cli'\n"
        f"  printf 'interactive-token\\n' > "
        f"'{session}/.gemini/antigravity-cli/antigravity-oauth-token'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    podman.chmod(0o755)
    return binary_dir, log


def _run(
    session: Path,
    home: Path,
    binary_dir: Path,
    log: Path,
    *,
    nested_podman: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(home),
            "MOCK_PODMAN_LOG": str(log),
            "PATH": f"{binary_dir}{os.pathsep}{environment['PATH']}",
        }
    )
    if nested_podman:
        environment["PIPELINE_NESTED_PODMAN"] = "1"
    else:
        environment.pop("PIPELINE_NESTED_PODMAN", None)
    return subprocess.run(
        [str(RUN_SH), str(session)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_run_sh_uses_hardened_evaluator_contract(
    tmp_path: Path,
) -> None:
    session = _session(tmp_path)
    home = _home_with_token(tmp_path)
    binary_dir, log = _mock_podman(tmp_path, session, auth_succeeds=True)

    result = _run(session, home, binary_dir, log)

    assert result.returncode == 0, result.stderr
    assert "Starting interactive login flow" not in result.stderr
    assert (session / "anti_karen" / "artifacts" / "karen_output.md").read_text() == (
        "Evaluation output\n"
    )

    calls = log.read_text(encoding="utf-8").splitlines()
    assert calls[0].startswith("build ")
    evaluation = next(call for call in calls if "run_evaluator" in call)
    assert "--cap-drop=ALL" in evaluation
    assert "--security-opt=no-new-privileges" in evaluation
    assert "--pids-limit=256" in evaluation
    assert "/docs:/app/session/docs:ro" in evaluation
    assert "/repos:/app/session/repos:ro" in evaluation
    assert "antigravity-oauth-token:ro" in evaluation
    assert "--dns=" not in evaluation


def test_run_sh_supports_explicit_interactive_login(tmp_path: Path) -> None:
    session = _session(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    binary_dir, log = _mock_podman(tmp_path, session, auth_succeeds=False)

    result = _run(session, home, binary_dir, log)

    assert result.returncode == 0, result.stderr
    assert "Starting interactive login flow" in result.stderr
    token = session / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"
    assert token.read_text(encoding="utf-8") == "interactive-token\n"
    assert (session / "anti_karen" / "artifacts" / "karen_output.md").is_file()


def test_nested_podman_applies_network_and_cgroup_boundaries_to_build_and_runs(
    tmp_path: Path,
) -> None:
    session = _session(tmp_path)
    home = _home_with_token(tmp_path)
    binary_dir, log = _mock_podman(tmp_path, session, auth_succeeds=True)

    result = _run(session, home, binary_dir, log, nested_podman=True)

    assert result.returncode == 0, result.stderr
    calls = log.read_text(encoding="utf-8").splitlines()
    build = calls[0]
    assert build.startswith("build ")
    assert "--isolation=chroot" in build
    assert "--network=host" in build
    assert "--cgroups=disabled" not in build

    run_calls = [call for call in calls if call.startswith("run ")]
    assert run_calls
    assert all("--cgroups=disabled" in call for call in run_calls)
    assert all("--network=host" in call for call in run_calls)


def test_evaluator_image_and_cli_are_non_privileged() -> None:
    dockerfile = (REPOSITORY_ROOT / "karen_guard" / "Dockerfile").read_text(encoding="utf-8")
    evaluator = (REPOSITORY_ROOT / "karen_guard" / "run_evaluator.sh").read_text(
        encoding="utf-8"
    )
    runner = RUN_SH.read_text(encoding="utf-8")

    assert "sudo" not in dockerfile
    assert "NOPASSWD" not in dockerfile
    assert "USER ${USER_ID}:${GROUP_ID}" in dockerfile
    assert "--sandbox" in evaluator
    assert "--dangerously-skip-permissions" not in evaluator
    assert "image exists" not in runner
    assert "--dns=8.8.8.8" not in runner


def test_evaluator_permissions_deny_unsandboxed_and_network_tools() -> None:
    config_path = REPOSITORY_ROOT / "config" / "agents" / "agy" / "config" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    permissions = config["userSettings"]["globalPermissionGrants"]

    assert "unsandboxed(*)" in permissions["deny"]
    assert "read_url(*)" in permissions["deny"]
    assert "mcp(*)" in permissions["deny"]
    assert "write_file(/app/session/out/**)" in permissions["allow"]


def test_outer_container_mounts_host_credentials_read_only() -> None:
    start_script = (REPOSITORY_ROOT / "start.sh").read_text(encoding="utf-8")
    dockerfile = (REPOSITORY_ROOT / "Dockerfile").read_text(encoding="utf-8")
    entrypoint = (REPOSITORY_ROOT / "entrypoint.sh").read_text(encoding="utf-8")

    assert '$ORIG_HOME/.gemini:/run/host-gemini:ro' in start_script
    assert '$ORIG_HOME/.gemini:/root/.gemini' not in start_script
    assert "cp -a /run/host-gemini/. /root/.gemini/" in entrypoint
    assert "    sudo \\" not in dockerfile


def test_outer_container_forwards_configurable_pipeline_roots() -> None:
    start_script = (REPOSITORY_ROOT / "start.sh").read_text(encoding="utf-8")

    assert 'DATA_HOST_DIR="${PIPELINE_DATA_DIR:-.data}"' in start_script
    assert 'RUNS_HOST_DIR="${PIPELINE_RUNS_DIR:-.runs}"' in start_script
    assert 'SESSION_CONTAINER_ROOT="${PIPELINE_SESSION_ROOT:-/tmp}"' in start_script
    assert '-e PIPELINE_DATA_DIR=/app/.data' in start_script
    assert '-e PIPELINE_RUNS_DIR=/app/.runs' in start_script
    assert '-e PIPELINE_SESSION_ROOT="$SESSION_CONTAINER_ROOT"' in start_script
    assert '-v "$DATA_HOST_DIR:/app/.data"' in start_script
    assert '-v "$RUNS_HOST_DIR:/app/.runs"' in start_script


def test_start_sh_mounts_custom_host_roots(tmp_path: Path) -> None:
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    docker_log = tmp_path / "docker.log"
    docker = binary_dir / "docker"
    docker.write_text(
        "#!/bin/sh\n"
        "printf 'CALL\\n' >> \"$MOCK_DOCKER_LOG\"\n"
        "printf '<%s>\\n' \"$@\" >> \"$MOCK_DOCKER_LOG\"\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    home = tmp_path / "home"
    (home / ".gemini").mkdir(parents=True)
    data_dir = tmp_path / "custom data"
    runs_dir = tmp_path / "custom runs"
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(home),
            "MOCK_DOCKER_LOG": str(docker_log),
            "PATH": f"{binary_dir}{os.pathsep}{environment['PATH']}",
            "PIPELINE_DATA_DIR": str(data_dir),
            "PIPELINE_RUNS_DIR": str(runs_dir),
            "PIPELINE_SESSION_ROOT": "/work/sessions",
        }
    )
    environment.pop("SUDO_USER", None)

    result = subprocess.run(
        [str(REPOSITORY_ROOT / "start.sh")],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    calls = docker_log.read_text(encoding="utf-8")
    assert f"<{data_dir}:/app/.data>" in calls
    assert f"<{runs_dir}:/app/.runs>" in calls
    assert "<PIPELINE_DATA_DIR=/app/.data>" in calls
    assert "<PIPELINE_RUNS_DIR=/app/.runs>" in calls
    assert "<PIPELINE_SESSION_ROOT=/work/sessions>" in calls


def test_outer_container_uses_explicit_nested_runtime_boundary() -> None:
    start_script = (REPOSITORY_ROOT / "start.sh").read_text(encoding="utf-8")

    assert "$DOCKER_CMD run -it --init --privileged" not in start_script
    assert "--cap-drop=ALL" in start_script
    assert "--cap-add=SYS_ADMIN" in start_script
    assert "--cap-add=SYS_RESOURCE" in start_script
    assert "--security-opt=apparmor=unconfined" in start_script
    assert "--security-opt=seccomp=unconfined" in start_script
    assert "--security-opt=no-new-privileges" in start_script
    assert "/var/run/docker.sock" not in start_script
    assert "PIPELINE_NESTED_PODMAN=1" in start_script
    runner = RUN_SH.read_text(encoding="utf-8")
    assert "ENGINE_BUILD_NESTED_FLAGS+=(--isolation=chroot --network=host)" in runner
    assert "ENGINE_RUN_NESTED_FLAGS+=(--cgroups=disabled --network=host)" in runner
