#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "${DIR}/.." && pwd)"
cd "${DIR}"

if command -v podman >/dev/null 2>&1; then
  CONTAINER_ENGINE="podman"
elif command -v docker >/dev/null 2>&1; then
  CONTAINER_ENGINE="docker"
else
  echo "Error: neither podman nor docker is available." >&2
  exit 1
fi

if [ "${CONTAINER_ENGINE}" = "docker" ] && ! docker ps >/dev/null 2>&1; then
  echo "Error: Docker is installed but the current user cannot access the daemon." >&2
  exit 1
fi

if [ "$#" -ne 1 ]; then
  echo "Usage: ./karen_guard/run.sh <absolute_session_dir>" >&2
  exit 1
fi

SESSION_DIR="$1"
if [ "${SESSION_DIR#/}" = "${SESSION_DIR}" ] || [ ! -d "${SESSION_DIR}" ]; then
  echo "Error: an existing absolute session directory is required: ${SESSION_DIR}" >&2
  exit 1
fi

SESSION_BASENAME="$(basename "${SESSION_DIR}")"
case "${SESSION_BASENAME}" in
  karen_guard_*) ;;
  *)
    echo "Error: unexpected session directory name: ${SESSION_BASENAME}" >&2
    exit 1
    ;;
esac
SESSION_ID="${SESSION_BASENAME#karen_guard_}"

HOST_UID="$(id -u)"
HOST_GID="$(id -g)"
if [ "${HOST_UID}" -eq 0 ]; then
  RUNTIME_UID=1000
  RUNTIME_GID=1000
else
  RUNTIME_UID="${HOST_UID}"
  RUNTIME_GID="${HOST_GID}"
fi
KAREN_HOME="/home/karen"

ENGINE_BUILD_NESTED_FLAGS=()
ENGINE_RUN_NESTED_FLAGS=()
if [ "${CONTAINER_ENGINE}" = "podman" ] && [ "${PIPELINE_NESTED_PODMAN:-0}" = "1" ]; then
  # Chroot isolation keeps build RUN steps independent of a cgroup tree the
  # outer container does not own. Both build and run share only the outer
  # container's network namespace, not the physical host network namespace.
  ENGINE_BUILD_NESTED_FLAGS+=(--isolation=chroot --network=host)
  ENGINE_RUN_NESTED_FLAGS+=(--cgroups=disabled --network=host)
fi

echo "Building Karen Guard image from the current source context..." >&2
"${CONTAINER_ENGINE}" build \
  "${ENGINE_BUILD_NESTED_FLAGS[@]}" \
  --file "${DIR}/Dockerfile" \
  --tag karen_guard \
  --build-arg USERNAME=karen \
  --build-arg USER_ID="${RUNTIME_UID}" \
  --build-arg GROUP_ID="${RUNTIME_GID}" \
  "${REPOSITORY_ROOT}" >&2

for agent_setup in "${REPOSITORY_ROOT}"/config/agents/*/setup.sh; do
  if [ -f "${agent_setup}" ]; then
    echo "Running agent setup: $(basename "$(dirname "${agent_setup}")")" >&2
    bash "${agent_setup}" "${SESSION_DIR}" "${RUNTIME_UID}" "${RUNTIME_GID}" "${KAREN_HOME}"
  fi
done

SESSION_GEMINI_DIR="${SESSION_DIR}/.gemini"
SESSION_AUTH_DIR="${SESSION_GEMINI_DIR}/antigravity-cli"
SESSION_TOKEN="${SESSION_AUTH_DIR}/antigravity-oauth-token"
HOST_TOKEN="${HOME}/.gemini/antigravity-cli/antigravity-oauth-token"

ENGINE_USER_FLAGS=()
if [ "${CONTAINER_ENGINE}" = "podman" ] && [ "${HOST_UID}" -ne 0 ]; then
  ENGINE_USER_FLAGS+=(--userns=keep-id)
fi

READ_ONLY_SUFFIX="ro"
READ_WRITE_SUFFIX="rw"
if [ "${CONTAINER_ENGINE}" = "podman" ]; then
  READ_ONLY_SUFFIX="ro,z"
  READ_WRITE_SUFFIX="rw,z"
fi

AUTH_MOUNTS=()
if [ -f "${SESSION_TOKEN}" ]; then
  AUTH_MOUNTS+=(
    --volume "${SESSION_TOKEN}:${KAREN_HOME}/.gemini/antigravity-cli/antigravity-oauth-token:${READ_ONLY_SUFFIX}"
  )
fi

echo "Checking Antigravity CLI authentication..." >&2
AUTH_SUCCESS=false
for attempt in 1 2 3; do
  if "${CONTAINER_ENGINE}" run --rm \
      "${ENGINE_USER_FLAGS[@]}" \
      "${ENGINE_RUN_NESTED_FLAGS[@]}" \
      --cap-drop=ALL \
      --security-opt=no-new-privileges \
      "${AUTH_MOUNTS[@]}" \
      karen_guard agy models >/dev/null 2>&1; then
    AUTH_SUCCESS=true
    break
  fi
  echo "Authentication check attempt ${attempt} failed." >&2
done

if [ "${AUTH_SUCCESS}" = false ]; then
  echo "Antigravity CLI is not authenticated. Starting interactive login flow..." >&2
  mkdir -p "${SESSION_AUTH_DIR}"
  "${CONTAINER_ENGINE}" run -it --rm \
    "${ENGINE_USER_FLAGS[@]}" \
    "${ENGINE_RUN_NESTED_FLAGS[@]}" \
    --cap-drop=ALL \
    --security-opt=no-new-privileges \
    --volume "${SESSION_AUTH_DIR}:${KAREN_HOME}/.gemini/antigravity-cli:${READ_WRITE_SUFFIX}" \
    karen_guard agy
fi

if [ ! -f "${SESSION_TOKEN}" ]; then
  echo "Error: authentication completed without producing the expected token." >&2
  exit 1
fi

if [ -d "$(dirname "${HOST_TOKEN}")" ]; then
  install -m 0600 "${SESSION_TOKEN}" "${HOST_TOKEN}"
fi

mkdir -p "${SESSION_DIR}/out" "${SESSION_DIR}/docs" "${SESSION_DIR}/repos" \
  "${SESSION_DIR}/anti_karen/artifacts" "${SESSION_DIR}/anti_karen/logs"
[ -f "${SESSION_DIR}/company_info.md" ] || touch "${SESSION_DIR}/company_info.md"
chown "${RUNTIME_UID}:${RUNTIME_GID}" "${SESSION_DIR}/out" "${SESSION_GEMINI_DIR}" \
  "${SESSION_AUTH_DIR}" "${SESSION_TOKEN}"

echo "Starting Karen Guard evaluation for session ${SESSION_ID}..." >&2
"${CONTAINER_ENGINE}" run --rm \
  "${ENGINE_USER_FLAGS[@]}" \
  "${ENGINE_RUN_NESTED_FLAGS[@]}" \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit=256 \
  --tmpfs /tmp:rw,nosuid,nodev,size=256m \
  --volume "${SESSION_DIR}/docs:/app/session/docs:${READ_ONLY_SUFFIX}" \
  --volume "${SESSION_DIR}/repos:/app/session/repos:${READ_ONLY_SUFFIX}" \
  --volume "${SESSION_DIR}/company_info.md:/app/session/company_info.md:${READ_ONLY_SUFFIX}" \
  --volume "${SESSION_DIR}/out:/app/session/out:${READ_WRITE_SUFFIX}" \
  --volume "${SESSION_TOKEN}:${KAREN_HOME}/.gemini/antigravity-cli/antigravity-oauth-token:${READ_ONLY_SUFFIX}" \
  karen_guard run_evaluator

if [ ! -f "${SESSION_DIR}/out/evaluation.md" ]; then
  echo "Error: Karen did not produce out/evaluation.md." >&2
  exit 1
fi

mv "${SESSION_DIR}/out/evaluation.md" \
  "${SESSION_DIR}/anti_karen/artifacts/karen_output.md"
echo "${SESSION_DIR}/anti_karen/artifacts/karen_output.md"
