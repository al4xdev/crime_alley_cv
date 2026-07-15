# Dependency Verification Guide

Verify dependencies on every run. Do not create a persistent “dependencies checked” marker:
installed tools, daemon access and credentials can change between executions.

## Supported environment

- **Host:** Linux. The nested-container boundary relies on Linux capabilities, seccomp, AppArmor
  integration where available and container namespaces.
- **Disk:** keep at least 10 GB free for the two images, build cache, run artifacts and cloned public
  repositories.
- **Authentication:** authenticate the selected CLI on the host first. `start.sh` mounts only its
  credential file, read-only; configuration and session history are recreated inside the container.

## Containerized execution

This is the normal path:

```fish
docker version
git --version
test -f ~/.gemini/antigravity-cli/antigravity-oauth-token # agy
test -f ~/.claude/.credentials.json                       # Claude Code
test -f ~/.codex/auth.json                                # Codex with file credential storage
./start.sh --agent codex
```

The host needs Docker daemon access without an interactive privilege prompt. Python, `uv`, Fish,
`jq`, Git, Podman and all three agent CLIs are installed inside the content-addressed outer image.
`start.sh` rebuilds that image from the current checkout before launching it. Karen's image is
built separately with only the selected CLI.

## Direct host execution

Running the runbook without the outer image additionally requires:

1. Python 3.13 or newer.
2. `uv` compatible with the checked-in `uv.lock` (the container and CI pin 0.11.28).
3. Fish, Git and `jq`.
4. Docker or Podman with permission to build and run containers.
5. An authenticated agy, Claude Code or Codex CLI capable of executing `main.md`.

Set the matching provider before asking a host-installed client to execute the runbook:

```fish
set -gx AGENT_PROVIDER codex
```

Verify the toolchain:

```fish
python --version
uv --version
fish --version
git --version
jq --version

if command -q podman
    podman version
else
    docker version
end

uv sync --frozen --group dev
```

## Development validation

These checks consume no provider quota:

```fish
uv run ruff check .
uv run mypy --strict harvey_guy tools/replay_pipeline.py
uv run pytest
bash -n start.sh entrypoint.sh karen_guard/run.sh karen_guard/run_evaluator.sh config/agents/agent.sh config/agents/*/setup.sh config/agents/*/run.sh
sh -n tools/configure_apt_snapshot.sh tools/install_agy.sh tools/install_claude.sh tools/install_codex.sh
fish -n boundaries/*.fish
jq empty config/agents/agy/config/config.json config/agents/claude/config/settings.json
```

CI repeats those checks, builds the outer orchestrator and builds a Karen evaluator image for each
provider. Real provider execution remains a credentialed smoke test; offline replay and mock
container tests cover the deterministic boundaries without quota.
