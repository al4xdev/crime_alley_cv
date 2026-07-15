#!/bin/bash
# start.sh — Launch the Crime Alley pipeline with a selected agent CLI.
set -euo pipefail

IMAGE_NAME="crime_alley_pipeline"
AGENT_PROVIDER="${AGENT_PROVIDER:-}"
SHELL_ONLY=false

usage() {
  echo "Usage: ./start.sh [--agent agy|claude|codex] [--shell]" >&2
}

auth_file_for() {
  case "$1" in
    agy) echo "${ORIG_HOME}/.gemini/antigravity-cli/antigravity-oauth-token" ;;
    claude) echo "${ORIG_HOME}/.claude/.credentials.json" ;;
    codex) echo "${ORIG_HOME}/.codex/auth.json" ;;
  esac
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

AUTH_FILE="$(auth_file_for "${AGENT_PROVIDER}")"
AUTH_HINT="Authenticate ${AGENT_PROVIDER} on the host first."

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
CELESTIAL_HOST_DIR="${CELESTIAL_DATA_DIR:-.celestial}"
SESSION_CONTAINER_ROOT="${PIPELINE_SESSION_ROOT:-/tmp}"
mkdir -p "${DATA_HOST_DIR}/docs" "${RUNS_HOST_DIR}" "${CELESTIAL_HOST_DIR}" || {
  echo "Error: Could not create pipeline data directories." >&2
  exit 1
}
DATA_HOST_DIR="$(realpath "${DATA_HOST_DIR}")"
RUNS_HOST_DIR="$(realpath "${RUNS_HOST_DIR}")"
CELESTIAL_HOST_DIR="$(realpath "${CELESTIAL_HOST_DIR}")"

CELESTIAL_ENABLED="${CELESTIAL_ENABLED:-}"
AGENT_MODEL="${AGENT_MODEL:-}"
CELESTIAL_JUDGE_PROVIDER="${CELESTIAL_JUDGE_PROVIDER:-}"
CELESTIAL_JUDGE_MODEL="${CELESTIAL_JUDGE_MODEL:-}"
CELESTIAL_CAPTURE_ID="${CELESTIAL_CAPTURE_ID:-capture-$(date -u +%Y%m%dT%H%M%SZ)-$$}"

if [ "${SHELL_ONLY}" = false ] && [ -z "${CELESTIAL_ENABLED}" ]; then
  if [ -t 0 ]; then
    echo >&2
    echo "Optional: enable The Celestial content benchmark?" >&2
    echo "WARNING: it runs a one-shot baseline plus repeated judging and can consume a lot of quota." >&2
    echo "WARNING: Claude/Codex execution permissions were constrained, but live quota/auth behavior" >&2
    echo "has intentionally not been exercised yet; keep it off until you have comfortable quota." >&2
    read -r -p "Enable The Celestial for this run? [y/N]: " celestial_answer
    case "${celestial_answer}" in
      y|Y|yes|YES) CELESTIAL_ENABLED=1 ;;
      *) CELESTIAL_ENABLED=0 ;;
    esac
  else
    CELESTIAL_ENABLED=0
  fi
fi

if [ "${CELESTIAL_ENABLED}" = "1" ]; then
  if [ -t 0 ]; then
    if [ -z "${AGENT_MODEL}" ]; then
      read -r -p "Exact ${AGENT_PROVIDER} executor model: " AGENT_MODEL
    fi
    if [ -z "${CELESTIAL_JUDGE_PROVIDER}" ]; then
      read -r -p "Fixed judge provider [agy|claude|codex]: " CELESTIAL_JUDGE_PROVIDER
    fi
    if [ -z "${CELESTIAL_JUDGE_MODEL}" ]; then
      read -r -p "Exact fixed judge model: " CELESTIAL_JUDGE_MODEL
    fi
  fi
  case "${CELESTIAL_JUDGE_PROVIDER}" in agy|claude|codex) ;; *)
    echo "Error: The Celestial requires a valid fixed judge provider." >&2; exit 2 ;;
  esac
  if [ -z "${AGENT_MODEL}" ] || [ -z "${CELESTIAL_JUDGE_MODEL}" ]; then
    echo "Error: The Celestial requires explicit executor and judge models." >&2
    exit 2
  fi
else
  CELESTIAL_ENABLED=0
fi

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
  -e CELESTIAL_DATA_DIR=/app/.celestial \
  -e CELESTIAL_CAPTURE_ID="${CELESTIAL_CAPTURE_ID}" \
  -e CELESTIAL_ENABLED="${CELESTIAL_ENABLED}" \
  -e AGENT_MODEL="${AGENT_MODEL}" \
  -e CELESTIAL_JUDGE_PROVIDER="${CELESTIAL_JUDGE_PROVIDER}" \
  -e CELESTIAL_JUDGE_MODEL="${CELESTIAL_JUDGE_MODEL}" \
  -v "${DATA_HOST_DIR}:/app/.data" \
  -v "${RUNS_HOST_DIR}:/app/.runs" \
  -v "${CELESTIAL_HOST_DIR}:/app/.celestial" \
  -v "${AUTH_FILE}:/run/host-agent-auth:ro" \
  "${IMAGE_NAME}" "${CONTAINER_COMMAND[@]}"

if [ "${SHELL_ONLY}" = true ] || [ "${CELESTIAL_ENABLED}" != "1" ]; then
  exit 0
fi

celestial_container() {
  local provider="$1"
  local auth_file="$2"
  shift 2
  "${DOCKER_CMD[@]}" run --init --rm \
    --cap-drop=ALL \
    --security-opt=no-new-privileges \
    -e AGENT_PROVIDER="${provider}" \
    -e CELESTIAL_DATA_DIR=/app/.celestial \
    -v "${CELESTIAL_HOST_DIR}:/app/.celestial" \
    -v "${auth_file}:/run/host-agent-auth:ro" \
    "${IMAGE_NAME}" "$@"
}

echo "The pipeline finished. Calculating the exact benchmark call estimate..." >&2
celestial_container "${AGENT_PROVIDER}" "${AUTH_FILE}" \
  uv run python -m the_celestial.cli plan --capture "${CELESTIAL_CAPTURE_ID}"

if [ -t 0 ]; then
  echo "WARNING: continuing now spends quota on the baseline and three repeated judgments per item." >&2
  read -r -p "Run the expensive benchmark now? Type RUN CELESTIAL: " quota_confirmation
  if [ "${quota_confirmation}" != "RUN CELESTIAL" ]; then
    echo "Benchmark deferred. The frozen capture remains in ${CELESTIAL_HOST_DIR}." >&2
    exit 0
  fi
else
  echo "Benchmark captured but deferred: interactive quota confirmation is required." >&2
  exit 0
fi

celestial_container "${AGENT_PROVIDER}" "${AUTH_FILE}" \
  uv run python -m the_celestial.cli baseline --capture "${CELESTIAL_CAPTURE_ID}"

JUDGE_AUTH_FILE="$(auth_file_for "${CELESTIAL_JUDGE_PROVIDER}")"
if [ ! -f "${JUDGE_AUTH_FILE}" ]; then
  echo "Error: judge credential file does not exist: ${JUDGE_AUTH_FILE}" >&2
  exit 1
fi
benchmark_json="$(celestial_container "${CELESTIAL_JUDGE_PROVIDER}" "${JUDGE_AUTH_FILE}" \
  uv run python -m the_celestial.cli judge --capture "${CELESTIAL_CAPTURE_ID}" \
  --confirm-high-quota)"
echo "${benchmark_json}"
benchmark_path="$(echo "${benchmark_json}" | jq -r .benchmark)"
celestial_container "${CELESTIAL_JUDGE_PROVIDER}" "${JUDGE_AUTH_FILE}" \
  uv run python -m the_celestial.cli report --benchmark "${benchmark_path}"
