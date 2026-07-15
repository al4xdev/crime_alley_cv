#!/bin/bash
# start.sh — Launch the Crime Alley pipeline with a selected agent CLI.
set -euo pipefail

IMAGE_NAME="crime_alley_pipeline"
AGENT_PROVIDER="${AGENT_PROVIDER:-}"
SHELL_ONLY=false

usage() {
  echo "Usage: ./start.sh [--agent agy|claude|codex] [--shell]" >&2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --agent)
      [ "$#" -ge 2 ] || { usage; exit 2; }
      AGENT_PROVIDER="$2"
      shift 2
      ;;
    --shell)
      SHELL_ONLY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [ -z "${AGENT_PROVIDER}" ]; then
  if [ ! -t 0 ]; then
    echo "Error: select an agent with --agent or AGENT_PROVIDER in non-interactive mode." >&2
    exit 2
  fi
  echo "Select the agent runtime:" >&2
  echo "  1) Antigravity (agy)" >&2
  echo "  2) Claude Code" >&2
  echo "  3) OpenAI Codex" >&2
  read -r -p "Agent [1-3]: " selection
  case "${selection}" in
    1) AGENT_PROVIDER=agy ;;
    2) AGENT_PROVIDER=claude ;;
    3) AGENT_PROVIDER=codex ;;
    *) echo "Error: invalid agent selection." >&2; exit 2 ;;
  esac
fi

case "${AGENT_PROVIDER}" in
  agy|claude|codex) ;;
  *) echo "Error: unsupported agent provider: ${AGENT_PROVIDER}" >&2; exit 2 ;;
esac

if docker ps >/dev/null 2>&1; then
  DOCKER_CMD=(docker)
elif command -v sudo >/dev/null 2>&1; then
  echo "Docker permission denied. Trying with sudo..." >&2
  DOCKER_CMD=(sudo docker)
else
  echo "Error: Docker is not accessible, and sudo is not available." >&2
  exit 1
fi

if [ -n "${SUDO_USER:-}" ]; then
  ORIG_HOME="$(getent passwd "${SUDO_USER}" | cut -d: -f6)"
else
  ORIG_HOME="${HOME}"
fi

case "${AGENT_PROVIDER}" in
  agy)
    AUTH_FILE="${ORIG_HOME}/.gemini/antigravity-cli/antigravity-oauth-token"
    AUTH_HINT="Authenticate agy on the host first."
    ;;
  claude)
    AUTH_FILE="${ORIG_HOME}/.claude/.credentials.json"
    AUTH_HINT="Run 'claude auth login' on the host first."
    ;;
  codex)
    AUTH_FILE="${ORIG_HOME}/.codex/auth.json"
    AUTH_HINT="Configure file credential storage and run 'codex login' on the host first."
    ;;
esac

if [ ! -f "${AUTH_FILE}" ]; then
  echo "Error: agent credential file does not exist: ${AUTH_FILE}" >&2
  echo "${AUTH_HINT}" >&2
  exit 1
fi

echo "Building global orchestrator image..." >&2
"${DOCKER_CMD[@]}" build -t "${IMAGE_NAME}" . || {
  echo "Error: Docker build failed." >&2
  exit 1
}

DATA_HOST_DIR="${PIPELINE_DATA_DIR:-.data}"
RUNS_HOST_DIR="${PIPELINE_RUNS_DIR:-.runs}"
SESSION_CONTAINER_ROOT="${PIPELINE_SESSION_ROOT:-/tmp}"
mkdir -p "${DATA_HOST_DIR}/docs" "${RUNS_HOST_DIR}" || {
  echo "Error: Could not create pipeline data directories." >&2
  exit 1
}
DATA_HOST_DIR="$(realpath "${DATA_HOST_DIR}")"
RUNS_HOST_DIR="$(realpath "${RUNS_HOST_DIR}")"

if [ "${SHELL_ONLY}" = true ]; then
  CONTAINER_COMMAND=(/usr/bin/fish)
else
  CONTAINER_COMMAND=(/app/config/agents/agent.sh "${AGENT_PROVIDER}" interactive /app/main.md)
fi

echo "Starting ${AGENT_PROVIDER} pipeline container..." >&2
"${DOCKER_CMD[@]}" run -it --init --rm \
  --cap-drop=ALL \
  --cap-add=AUDIT_WRITE \
  --cap-add=CHOWN \
  --cap-add=DAC_OVERRIDE \
  --cap-add=FOWNER \
  --cap-add=FSETID \
  --cap-add=KILL \
  --cap-add=MKNOD \
  --cap-add=NET_BIND_SERVICE \
  --cap-add=NET_RAW \
  --cap-add=SETFCAP \
  --cap-add=SETGID \
  --cap-add=SETPCAP \
  --cap-add=SETUID \
  --cap-add=SYS_ADMIN \
  --cap-add=SYS_CHROOT \
  --cap-add=SYS_RESOURCE \
  --security-opt=apparmor=unconfined \
  --security-opt=seccomp=unconfined \
  --security-opt=no-new-privileges \
  -e AGENT_PROVIDER="${AGENT_PROVIDER}" \
  -e PIPELINE_NESTED_PODMAN=1 \
  -e PIPELINE_DATA_DIR=/app/.data \
  -e PIPELINE_RUNS_DIR=/app/.runs \
  -e PIPELINE_SESSION_ROOT="${SESSION_CONTAINER_ROOT}" \
  -v "${DATA_HOST_DIR}:/app/.data" \
  -v "${RUNS_HOST_DIR}:/app/.runs" \
  -v "${AUTH_FILE}:/run/host-agent-auth:ro" \
  "${IMAGE_NAME}" "${CONTAINER_COMMAND[@]}"
