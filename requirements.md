# Dependency Verification Guide

Verify dependencies on every run. Do not create a persistent “dependencies checked” marker:
installed tools, daemon access and credentials can change between executions.

## Supported environment

- **Host:** Linux. The nested-container boundary relies on Linux capabilities, seccomp, AppArmor
  integration where available and container namespaces.
- **Disk:** keep at least 10 GB free for the two images, build cache, run artifacts and cloned public
  repositories.
- **Authentication:** authenticate `agy` on the host first. `start.sh` requires
  `~/.gemini/antigravity-cli/antigravity-oauth-token` and mounts the credential directory read-only.

## Containerized execution

This is the normal path:

```fish
docker version
git --version
test -f ~/.gemini/antigravity-cli/antigravity-oauth-token
./start.sh
```

The host needs Docker daemon access without an interactive privilege prompt. Python, `uv`, Fish,
`jq`, Git, Podman and `agy` are installed inside the content-addressed outer image. `start.sh`
rebuilds that image from the current checkout before launching it.

## Direct host execution

Running the runbook without the outer image additionally requires:

1. Python 3.13 or newer.
2. `uv` compatible with the checked-in `uv.lock` (the container and CI pin 0.11.28).
3. Fish, Git and `jq`.
4. Docker or Podman with permission to build and run containers.
5. An authenticated agent client capable of executing `@main.md`.

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
bash -n start.sh entrypoint.sh karen_guard/run.sh karen_guard/run_evaluator.sh
sh -n tools/configure_apt_snapshot.sh tools/install_agy.sh
fish -n boundaries/*.fish
jq empty config/agents/agy/config/config.json
```

CI repeats those checks and builds both the outer orchestrator and Karen evaluator images. Real
provider execution is intentionally excluded while `agy` quota is unavailable; the offline replay
and mock container tests cover the deterministic boundaries.
