#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "${DIR}/.." && pwd)"
cd "${DIR}"

if [ "$#" -ne 3 ] && [ "$#" -ne 5 ]; then
  echo "Usage: ./karen_guard/run.sh --agent <agy|claude|codex> [--state <state.json>] <absolute_session_dir>" >&2
  exit 2
fi
if [ "$1" != "--agent" ]; then
  echo "Error: --agent must be the first argument." >&2
  exit 2
fi
AGENT_PROVIDER="$2"
STATE_PATH=""
if [ "$#" -eq 5 ]; then
  if [ "$3" != "--state" ]; then
    echo "Error: expected --state after the agent provider." >&2
    exit 2
  fi
  STATE_PATH="$4"
  SESSION_DIR="$5"
else
  SESSION_DIR="$3"
fi
case "${AGENT_PROVIDER}" in
  agy|claude|codex) ;;
  *) echo "Error: unsupported agent provider: ${AGENT_PROVIDER}" >&2; exit 2 ;;
esac

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

if [ "${SESSION_DIR#/}" = "${SESSION_DIR}" ] || [ ! -d "${SESSION_DIR}" ]; then
  echo "Error: an existing absolute session directory is required: ${SESSION_DIR}" >&2
  exit 1
fi
SESSION_BASENAME="$(basename "${SESSION_DIR}")"
case "${SESSION_BASENAME}" in
  karen_guard_*) ;;
  *) echo "Error: unexpected session directory name: ${SESSION_BASENAME}" >&2; exit 1 ;;
esac
SESSION_ID="${SESSION_BASENAME#karen_guard_}"

if [ -n "${STATE_PATH}" ]; then
  if [ "${STATE_PATH#/}" = "${STATE_PATH}" ] || [ ! -f "${STATE_PATH}" ]; then
    echo "Error: --state requires an existing absolute state file: ${STATE_PATH}" >&2
    exit 1
  fi
  STATE_AGENT_PROVIDER="$(jq -er '.agent_provider // "agy"' "${STATE_PATH}")"
  STATE_SESSION_DIR="$(jq -er '.current_session_dir' "${STATE_PATH}")"
  if [ "${STATE_AGENT_PROVIDER}" != "${AGENT_PROVIDER}" ]; then
    echo "Error: agent provider ${AGENT_PROVIDER} diverges from state provider ${STATE_AGENT_PROVIDER}." >&2
    exit 1
  fi
  if [ "${STATE_SESSION_DIR}" != "${SESSION_DIR}" ]; then
    echo "Error: session directory diverges from the active state session." >&2
    exit 1
  fi
fi

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
IMAGE_NAME="karen_guard-${AGENT_PROVIDER}"

ENGINE_BUILD_NESTED_FLAGS=()
ENGINE_RUN_NESTED_FLAGS=()
if [ "${CONTAINER_ENGINE}" = "podman" ] && [ "${PIPELINE_NESTED_PODMAN:-0}" = "1" ]; then
  ENGINE_BUILD_NESTED_FLAGS+=(--isolation=chroot --network=host)
  ENGINE_RUN_NESTED_FLAGS+=(--cgroups=disabled --network=host)
fi

echo "Building Karen Guard ${AGENT_PROVIDER} image from the current source context..." >&2
"${CONTAINER_ENGINE}" build \
  "${ENGINE_BUILD_NESTED_FLAGS[@]}" \
  --file "${DIR}/Dockerfile" \
  --tag "${IMAGE_NAME}" \
  --build-arg AGENT_PROVIDER="${AGENT_PROVIDER}" \
  --build-arg USERNAME=karen \
  --build-arg USER_ID="${RUNTIME_UID}" \
  --build-arg GROUP_ID="${RUNTIME_GID}" \
  "${REPOSITORY_ROOT}" >&2

"${REPOSITORY_ROOT}/config/agents/agent.sh" "${AGENT_PROVIDER}" setup evaluator \
  "${SESSION_DIR}" "${RUNTIME_UID}" "${RUNTIME_GID}" "${KAREN_HOME}"

case "${AGENT_PROVIDER}" in
  agy)
    SESSION_AGENT_HOME="${SESSION_DIR}/.gemini"
    SESSION_AUTH_DIR="${SESSION_AGENT_HOME}/antigravity-cli"
    SESSION_CREDENTIAL="${SESSION_AUTH_DIR}/antigravity-oauth-token"
    HOST_CREDENTIAL="${HOME}/.gemini/antigravity-cli/antigravity-oauth-token"
    CONTAINER_AUTH_DIR="${KAREN_HOME}/.gemini/antigravity-cli"
    CONTAINER_CREDENTIAL="${CONTAINER_AUTH_DIR}/antigravity-oauth-token"
    ;;
  claude)
    SESSION_AGENT_HOME="${SESSION_DIR}/.claude"
    SESSION_AUTH_DIR="${SESSION_AGENT_HOME}"
    SESSION_CREDENTIAL="${SESSION_AUTH_DIR}/.credentials.json"
    HOST_CREDENTIAL="${HOME}/.claude/.credentials.json"
    CONTAINER_AUTH_DIR="${KAREN_HOME}/.claude"
    CONTAINER_CREDENTIAL="${CONTAINER_AUTH_DIR}/.credentials.json"
    ;;
  codex)
    SESSION_AGENT_HOME="${SESSION_DIR}/.codex"
    SESSION_AUTH_DIR="${SESSION_AGENT_HOME}"
    SESSION_CREDENTIAL="${SESSION_AUTH_DIR}/auth.json"
    HOST_CREDENTIAL="${HOME}/.codex/auth.json"
    CONTAINER_AUTH_DIR="${KAREN_HOME}/.codex"
    CONTAINER_CREDENTIAL="${CONTAINER_AUTH_DIR}/auth.json"
    ;;
esac

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
if [ -f "${SESSION_CREDENTIAL}" ]; then
  AUTH_MOUNTS+=(--volume "${SESSION_CREDENTIAL}:${CONTAINER_CREDENTIAL}:${READ_ONLY_SUFFIX}")
fi

echo "Checking ${AGENT_PROVIDER} authentication..." >&2
AUTH_SUCCESS=false
for attempt in 1 2 3; do
  if "${CONTAINER_ENGINE}" run --rm \
      "${ENGINE_USER_FLAGS[@]}" \
      "${ENGINE_RUN_NESTED_FLAGS[@]}" \
      --cap-drop=ALL \
      --security-opt=no-new-privileges \
      "${AUTH_MOUNTS[@]}" \
      "${IMAGE_NAME}" /opt/agents/agent.sh "${AGENT_PROVIDER}" auth-check \
      >/dev/null 2>&1; then
    AUTH_SUCCESS=true
    break
  fi
  echo "Authentication check attempt ${attempt} failed." >&2
done

if [ "${AUTH_SUCCESS}" = false ]; then
  echo "${AGENT_PROVIDER} is not authenticated. Starting interactive login flow..." >&2
  mkdir -p "${SESSION_AUTH_DIR}"
  chown -R "${RUNTIME_UID}:${RUNTIME_GID}" "${SESSION_AGENT_HOME}"
  "${CONTAINER_ENGINE}" run -it --rm \
    "${ENGINE_USER_FLAGS[@]}" \
    "${ENGINE_RUN_NESTED_FLAGS[@]}" \
    --cap-drop=ALL \
    --security-opt=no-new-privileges \
    --volume "${SESSION_AUTH_DIR}:${CONTAINER_AUTH_DIR}:${READ_WRITE_SUFFIX}" \
    "${IMAGE_NAME}" /opt/agents/agent.sh "${AGENT_PROVIDER}" login
fi

if [ ! -f "${SESSION_CREDENTIAL}" ]; then
  echo "Error: authentication completed without producing the expected credential." >&2
  exit 1
fi
if [ -d "$(dirname "${HOST_CREDENTIAL}")" ]; then
  install -m 0600 "${SESSION_CREDENTIAL}" "${HOST_CREDENTIAL}"
fi

mkdir -p "${SESSION_DIR}/out" "${SESSION_DIR}/docs" "${SESSION_DIR}/repos" \
  "${SESSION_DIR}/anti_karen/artifacts" "${SESSION_DIR}/anti_karen/logs"
[ -f "${SESSION_DIR}/company_info.md" ] || touch "${SESSION_DIR}/company_info.md"
chown "${RUNTIME_UID}:${RUNTIME_GID}" "${SESSION_DIR}/out" "${SESSION_AGENT_HOME}" \
  "${SESSION_AUTH_DIR}" "${SESSION_CREDENTIAL}"

echo "Starting Karen Guard ${AGENT_PROVIDER} evaluation for session ${SESSION_ID}..." >&2
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
  --volume "${SESSION_CREDENTIAL}:${CONTAINER_CREDENTIAL}:${READ_ONLY_SUFFIX}" \
  "${IMAGE_NAME}" run_evaluator

if [ ! -s "${SESSION_DIR}/out/evaluation.md" ]; then
  echo "Error: Karen did not produce a non-empty out/evaluation.md." >&2
  exit 1
fi
mv "${SESSION_DIR}/out/evaluation.md" \
  "${SESSION_DIR}/anti_karen/artifacts/karen_output.md"
echo "${SESSION_DIR}/anti_karen/artifacts/karen_output.md"
