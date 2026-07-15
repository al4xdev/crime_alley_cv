from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RUN_SH = REPOSITORY_ROOT / "karen_guard" / "run.sh"
PROVIDERS = ("agy", "claude", "codex")


def _session(tmp_path: Path) -> Path:
    session = tmp_path / "karen_guard_test-session"
    for directory in ("docs", "repos", "out", "anti_karen"):
        (session / directory).mkdir(parents=True, exist_ok=True)
    (session / "company_info.md").write_text("# Company\n", encoding="utf-8")
    return session


def _credential_paths(root: Path, provider: str) -> tuple[Path, Path]:
    if provider == "agy":
        relative = Path(".gemini/antigravity-cli/antigravity-oauth-token")
    elif provider == "claude":
        relative = Path(".claude/.credentials.json")
    else:
        relative = Path(".codex/auth.json")
    return root / relative, relative


def _home_with_credential(tmp_path: Path, provider: str) -> Path:
    home = tmp_path / "home"
    credential, _ = _credential_paths(home, provider)
    credential.parent.mkdir(parents=True)
    credential.write_text(f"mock-{provider}-credential\n", encoding="utf-8")
    credential.chmod(0o600)
    return home


def _mock_podman(
    tmp_path: Path,
    session: Path,
    provider: str,
    *,
    auth_succeeds: bool,
) -> tuple[Path, Path]:
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    log = tmp_path / "podman.log"
    podman = binary_dir / "podman"
    auth_status = "0" if auth_succeeds else "1"
    session_credential, _ = _credential_paths(session, provider)
    podman.write_text(
        "#!/bin/sh\n"
        'printf \'%s\\n\' "$*" >> "$MOCK_PODMAN_LOG"\n'
        'if [ "$1" = "build" ]; then exit 0; fi\n'
        'if echo "$*" | grep -q "auth-check"; then exit '
        + auth_status
        + "; fi\n"
        'if echo "$*" | grep -q " run_evaluator"; then\n'
        f"  printf 'Evaluation output\\n' > '{session}/out/evaluation.md'\n"
        "  exit 0\n"
        "fi\n"
        'if echo "$*" | grep -q " login"; then\n'
        f"  mkdir -p '{session_credential.parent}'\n"
        f"  printf 'interactive-{provider}-credential\\n' > '{session_credential}'\n"
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
    provider: str,
    *,
    nested_podman: bool = False,
    state: Path | None = None,
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
    arguments = [str(RUN_SH), "--agent", provider]
    if state is not None:
        arguments.extend(["--state", str(state)])
    arguments.append(str(session))
    return subprocess.run(
        arguments,
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("provider", PROVIDERS)
def test_run_sh_uses_selected_hardened_evaluator_contract(
    tmp_path: Path, provider: str
) -> None:
    session = _session(tmp_path)
    home = _home_with_credential(tmp_path, provider)
    binary_dir, log = _mock_podman(
        tmp_path, session, provider, auth_succeeds=True
    )

    result = _run(session, home, binary_dir, log, provider)

    assert result.returncode == 0, result.stderr
    assert "Starting interactive login flow" not in result.stderr
    assert (session / "anti_karen/artifacts/karen_output.md").read_text() == (
        "Evaluation output\n"
    )
    calls = log.read_text(encoding="utf-8").splitlines()
    build = calls[0]
    assert f"--build-arg AGENT_PROVIDER={provider}" in build
    assert f"--tag karen_guard-{provider}" in build
    evaluation = next(call for call in calls if " run_evaluator" in call)
    assert "--cap-drop=ALL" in evaluation
    assert "--security-opt=no-new-privileges" in evaluation
    assert "--pids-limit=256" in evaluation
    assert "/docs:/app/session/docs:ro" in evaluation
    assert "/repos:/app/session/repos:ro" in evaluation
    credential, _ = _credential_paths(session, provider)
    assert f"{credential}:" in evaluation


@pytest.mark.parametrize("provider", PROVIDERS)
def test_run_sh_supports_provider_interactive_login(
    tmp_path: Path, provider: str
) -> None:
    session = _session(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    binary_dir, log = _mock_podman(
        tmp_path, session, provider, auth_succeeds=False
    )

    result = _run(session, home, binary_dir, log, provider)

    assert result.returncode == 0, result.stderr
    assert "Starting interactive login flow" in result.stderr
    credential, _ = _credential_paths(session, provider)
    assert credential.read_text(encoding="utf-8") == (
        f"interactive-{provider}-credential\n"
    )


def test_run_sh_rejects_unknown_provider(tmp_path: Path) -> None:
    session = _session(tmp_path)
    result = subprocess.run(
        [str(RUN_SH), "--agent", "unknown", str(session)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "unsupported agent provider" in result.stderr


def test_run_sh_rejects_provider_that_diverges_from_state(tmp_path: Path) -> None:
    session = _session(tmp_path)
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps(
            {"agent_provider": "claude", "current_session_dir": str(session)}
        ),
        encoding="utf-8",
    )
    home = _home_with_credential(tmp_path, "codex")
    binary_dir, log = _mock_podman(
        tmp_path, session, "codex", auth_succeeds=True
    )

    result = _run(session, home, binary_dir, log, "codex", state=state)

    assert result.returncode == 1
    assert "diverges from state provider claude" in result.stderr
    assert not log.exists()


def test_nested_podman_applies_network_and_cgroup_boundaries(tmp_path: Path) -> None:
    session = _session(tmp_path)
    home = _home_with_credential(tmp_path, "agy")
    binary_dir, log = _mock_podman(tmp_path, session, "agy", auth_succeeds=True)

    result = _run(
        session, home, binary_dir, log, "agy", nested_podman=True
    )

    assert result.returncode == 0, result.stderr
    calls = log.read_text(encoding="utf-8").splitlines()
    assert "--isolation=chroot" in calls[0]
    assert "--network=host" in calls[0]
    run_calls = [call for call in calls if call.startswith("run ")]
    assert run_calls
    assert all("--cgroups=disabled" in call for call in run_calls)
    assert all("--network=host" in call for call in run_calls)


def test_evaluator_images_and_cli_wrappers_are_non_privileged() -> None:
    dockerfile = (REPOSITORY_ROOT / "karen_guard/Dockerfile").read_text()
    runner = RUN_SH.read_text(encoding="utf-8")
    agy = (REPOSITORY_ROOT / "config/agents/agy/run.sh").read_text()
    claude = (REPOSITORY_ROOT / "config/agents/claude/run.sh").read_text()
    codex = (REPOSITORY_ROOT / "config/agents/codex/run.sh").read_text()

    assert "sudo" not in dockerfile
    assert "NOPASSWD" not in dockerfile
    assert "USER ${USER_ID}:${GROUP_ID}" in dockerfile
    assert "--dangerously-skip-permissions" not in "\n".join((agy, claude, codex))
    assert "--sandbox" in agy
    assert "--permission-mode dontAsk" in claude
    assert "--sandbox danger-full-access" in codex
    assert 'approval_policy="never"' in codex
    assert "--dns=8.8.8.8" not in runner


def test_provider_configs_disable_network_tools_and_memories() -> None:
    agy_config = json.loads(
        (REPOSITORY_ROOT / "config/agents/agy/config/config.json").read_text()
    )
    claude_config = json.loads(
        (REPOSITORY_ROOT / "config/agents/claude/config/settings.json").read_text()
    )
    codex_config = (
        REPOSITORY_ROOT / "config/agents/codex/config/config.toml"
    ).read_text()

    agy_denies = agy_config["userSettings"]["globalPermissionGrants"]["deny"]
    assert "read_url(*)" in agy_denies
    assert "mcp(*)" in agy_denies
    assert "WebFetch" in claude_config["permissions"]["deny"]
    assert "WebSearch" in claude_config["permissions"]["deny"]
    assert 'web_search = "disabled"' in codex_config
    assert "memories = false" in codex_config


def _mock_docker(tmp_path: Path) -> tuple[Path, Path]:
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    log = tmp_path / "docker.log"
    docker = binary_dir / "docker"
    docker.write_text(
        "#!/bin/sh\n"
        "printf 'CALL\\n' >> \"$MOCK_DOCKER_LOG\"\n"
        "printf '<%s>\\n' \"$@\" >> \"$MOCK_DOCKER_LOG\"\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    return binary_dir, log


@pytest.mark.parametrize("provider", PROVIDERS)
def test_start_sh_mounts_only_selected_credential(
    tmp_path: Path, provider: str
) -> None:
    binary_dir, log = _mock_docker(tmp_path)
    home = _home_with_credential(tmp_path, provider)
    data_dir = tmp_path / "custom data"
    runs_dir = tmp_path / "custom runs"
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(home),
            "MOCK_DOCKER_LOG": str(log),
            "PATH": f"{binary_dir}{os.pathsep}{environment['PATH']}",
            "PIPELINE_DATA_DIR": str(data_dir),
            "PIPELINE_RUNS_DIR": str(runs_dir),
            "PIPELINE_SESSION_ROOT": "/work/sessions",
        }
    )
    environment.pop("SUDO_USER", None)

    result = subprocess.run(
        [str(REPOSITORY_ROOT / "start.sh"), "--agent", provider],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    calls = log.read_text(encoding="utf-8")
    credential, _ = _credential_paths(home, provider)
    assert f"<{credential}:/run/host-agent-auth:ro>" in calls
    assert f"<AGENT_PROVIDER={provider}>" in calls
    assert f"<{data_dir}:/app/.data>" in calls
    assert f"<{runs_dir}:/app/.runs>" in calls
    assert "<PIPELINE_SESSION_ROOT=/work/sessions>" in calls
    assert f"<{provider}>" in calls


def test_start_sh_requires_provider_without_tty(tmp_path: Path) -> None:
    binary_dir, _ = _mock_docker(tmp_path)
    environment = os.environ.copy()
    environment["PATH"] = f"{binary_dir}{os.pathsep}{environment['PATH']}"
    environment.pop("AGENT_PROVIDER", None)
    result = subprocess.run(
        [str(REPOSITORY_ROOT / "start.sh")],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "select an agent" in result.stderr


def test_outer_container_uses_explicit_nested_runtime_boundary() -> None:
    start_script = (REPOSITORY_ROOT / "start.sh").read_text(encoding="utf-8")
    assert "--privileged" not in start_script
    assert "--cap-drop=ALL" in start_script
    assert "--cap-add=SYS_ADMIN" in start_script
    assert "--security-opt=apparmor=unconfined" in start_script
    assert "--security-opt=seccomp=unconfined" in start_script
    assert "--security-opt=no-new-privileges" in start_script
    assert "/var/run/docker.sock" not in start_script
    runner = RUN_SH.read_text(encoding="utf-8")
    assert "ENGINE_BUILD_NESTED_FLAGS+=(--isolation=chroot --network=host)" in runner
    assert "ENGINE_RUN_NESTED_FLAGS+=(--cgroups=disabled --network=host)" in runner
