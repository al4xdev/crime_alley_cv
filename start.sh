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

CELESTIAL_ENABLED="${CELESTIAL_ENABLED:-}"
AGENT_MODEL="${AGENT_MODEL:-}"
CELESTIAL_JUDGE_PROVIDER="${CELESTIAL_JUDGE_PROVIDER:-}"
CELESTIAL_JUDGE_MODEL="${CELESTIAL_JUDGE_MODEL:-}"
CELESTIAL_CAPTURE_ID="${CELESTIAL_CAPTURE_ID:-capture-$(date -u +%Y%m%dT%H%M%SZ)-$$}"

if [ "${SHELL_ONLY}" = false ] && [ -z "${CELESTIAL_ENABLED}" ]; then
  if [ -t 0 ]; then
    echo >&2
    echo "Optional: enable The Celestial content benchmark?" >&2
    echo "WARNING: it runs a baseline plus repeated judging and can consume substantial quota." >&2
    echo "WARNING: live Claude/Codex enforcement remains intentionally untested." >&2
    read -r -p "Enable The Celestial for this run? [y/N]: " celestial_answer
    case "${celestial_answer}" in y|Y|yes|YES) CELESTIAL_ENABLED=1 ;; *) CELESTIAL_ENABLED=0 ;; esac
  else
    CELESTIAL_ENABLED=0
  fi
fi

if [ "${CELESTIAL_ENABLED}" = "1" ]; then
  if [ -t 0 ]; then
    [ -n "${AGENT_MODEL}" ] || read -r -p "Versioned ${AGENT_PROVIDER} executor model: " AGENT_MODEL
    [ -n "${CELESTIAL_JUDGE_PROVIDER}" ] || read -r -p "Fixed judge [claude|codex]: " CELESTIAL_JUDGE_PROVIDER
    [ -n "${CELESTIAL_JUDGE_MODEL}" ] || read -r -p "Versioned fixed judge model: " CELESTIAL_JUDGE_MODEL
  fi
  if [ "${AGENT_PROVIDER}" = "agy" ]; then
    echo "Error: agy is fail-closed for Celestial calls until no-tool enforcement is verifiable." >&2
    exit 2
  fi
  case "${CELESTIAL_JUDGE_PROVIDER}" in claude|codex) ;; *)
    echo "Error: the Celestial judge must be claude or codex." >&2; exit 2 ;;
  esac
  if [ "${AGENT_PROVIDER}" = "claude" ] && [[ ! "${AGENT_MODEL}" =~ ^claude-[a-z0-9-]+-[0-9]{8}$ ]]; then
    echo "Error: Claude requires a complete versioned model ID." >&2; exit 2
  fi
  if [ "${AGENT_PROVIDER}" = "codex" ] && [[ ! "${AGENT_MODEL}" =~ ^gpt-[0-9]+(\.[0-9]+)+(-[a-z0-9.-]+)?$ ]]; then
    echo "Error: Codex requires a versioned model ID." >&2; exit 2
  fi
  if [ "${CELESTIAL_JUDGE_PROVIDER}" = "claude" ] && [[ ! "${CELESTIAL_JUDGE_MODEL}" =~ ^claude-[a-z0-9-]+-[0-9]{8}$ ]]; then
    echo "Error: Claude judge requires a complete versioned model ID." >&2; exit 2
  fi
  if [ "${CELESTIAL_JUDGE_PROVIDER}" = "codex" ] && [[ ! "${CELESTIAL_JUDGE_MODEL}" =~ ^gpt-[0-9]+(\.[0-9]+)+(-[a-z0-9.-]+)?$ ]]; then
    echo "Error: Codex judge requires a versioned model ID." >&2; exit 2
  fi
else
  CELESTIAL_ENABLED=0
fi

AUTH_FILE="$(auth_file_for "${AGENT_PROVIDER}")"
AUTH_HINT="Authenticate ${AGENT_PROVIDER} on the host first."

if [ ! -f "${AUTH_FILE}" ]; then
  echo "Error: agent credential file does not exist: ${AUTH_FILE}" >&2
  echo "${AUTH_HINT}" >&2
  exit 1
fi

if [ "${CELESTIAL_ENABLED}" = "1" ]; then
  JUDGE_AUTH_FILE="$(auth_file_for "${CELESTIAL_JUDGE_PROVIDER}")"
  if [ ! -f "${JUDGE_AUTH_FILE}" ]; then
    echo "Error: judge credential file does not exist: ${JUDGE_AUTH_FILE}" >&2
    exit 1
  fi
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

if [ "${CELESTIAL_ENABLED}" = "1" ]; then
  echo "Building dedicated Celestial ${AGENT_PROVIDER} image..." >&2
  "${DOCKER_CMD[@]}" build -f the_celestial/Dockerfile \
    --build-arg AGENT_PROVIDER="${AGENT_PROVIDER}" \
    -t "celestial-${AGENT_PROVIDER}" .
  if [ "${CELESTIAL_JUDGE_PROVIDER}" != "${AGENT_PROVIDER}" ]; then
    echo "Building dedicated Celestial ${CELESTIAL_JUDGE_PROVIDER} image..." >&2
    "${DOCKER_CMD[@]}" build -f the_celestial/Dockerfile \
      --build-arg AGENT_PROVIDER="${CELESTIAL_JUDGE_PROVIDER}" \
      -t "celestial-${CELESTIAL_JUDGE_PROVIDER}" .
  fi
fi

celestial_container() {
  local provider="$1"
  local auth_file="$2"
  shift 2
  "${DOCKER_CMD[@]}" run --init --rm --read-only \
    --cap-drop=ALL \
    --pids-limit=128 \
    --security-opt=no-new-privileges \
    --tmpfs /tmp:rw,nosuid,nodev,size=128m \
    --tmpfs /home/celestial:rw,nosuid,nodev,size=32m,mode=0700,uid=1000,gid=1000 \
    -e AGENT_PROVIDER="${provider}" \
    -e CELESTIAL_DATA_DIR=/app/.celestial \
    -v "${CELESTIAL_HOST_DIR}:/app/.celestial:rw" \
    -v "${auth_file}:/run/host-agent-auth:ro" \
    "celestial-${provider}" "$@"
}

if [ "${CELESTIAL_ENABLED}" = "1" ]; then
  celestial_container "${AGENT_PROVIDER}" "${AUTH_FILE}" \
    python -m the_celestial.cli capability --provider "${AGENT_PROVIDER}" --model "${AGENT_MODEL}"
  celestial_container "${CELESTIAL_JUDGE_PROVIDER}" "${JUDGE_AUTH_FILE}" \
    python -m the_celestial.cli capability --provider "${CELESTIAL_JUDGE_PROVIDER}" \
    --model "${CELESTIAL_JUDGE_MODEL}"
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

echo "The pipeline finished. Calculating the exact benchmark call estimate..." >&2
plan_json="$(celestial_container "${AGENT_PROVIDER}" "${AUTH_FILE}" \
  python -m the_celestial.cli plan --capture "${CELESTIAL_CAPTURE_ID}")"
echo "${plan_json}"
plan_digest="$(echo "${plan_json}" | jq -er .plan_digest)"
confirmation_token="RUN ${plan_digest:0:12}"

if [ -t 0 ]; then
  echo "WARNING: continuing now spends quota on the baseline and three repeated judgments per item." >&2
  read -r -p "Run the expensive benchmark now? Type ${confirmation_token}: " quota_confirmation
  if [ "${quota_confirmation}" != "${confirmation_token}" ]; then
    echo "Benchmark deferred. The frozen capture remains in ${CELESTIAL_HOST_DIR}." >&2
    exit 0
  fi
else
  echo "Benchmark captured but deferred: interactive quota confirmation is required." >&2
  exit 0
fi

celestial_container "${AGENT_PROVIDER}" "${AUTH_FILE}" \
  python -m the_celestial.cli baseline --capture "${CELESTIAL_CAPTURE_ID}" \
  --accept-plan "${plan_digest}"

benchmark_json="$(celestial_container "${CELESTIAL_JUDGE_PROVIDER}" "${JUDGE_AUTH_FILE}" \
  python -m the_celestial.cli judge --capture "${CELESTIAL_CAPTURE_ID}" \
  --accept-plan "${plan_digest}")"
echo "${benchmark_json}"
benchmark_path="$(echo "${benchmark_json}" | jq -r .benchmark)"
celestial_container "${CELESTIAL_JUDGE_PROVIDER}" "${JUDGE_AUTH_FILE}" \
  python -m the_celestial.cli report --benchmark "${benchmark_path}"
