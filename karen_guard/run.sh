#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Detect container engine: prefer Podman, fallback to Docker
if command -v podman >/dev/null 2>&1; then
  CONTAINER_ENGINE="podman"
elif command -v docker >/dev/null 2>&1; then
  CONTAINER_ENGINE="docker"
else
  echo "Error: Neither podman nor docker found on the host system." >&2
  exit 1
fi

if [ "$CONTAINER_ENGINE" = "docker" ]; then
  if ! docker ps >/dev/null 2>&1; then
    echo "No permission to access Docker socket. Retrying command via 'sg docker'..." >&2
    exec sg docker -c "$0 $(printf '%q ' "$@")"
  fi
fi

if [ -z "$1" ]; then
  echo "Usage: ./run.sh <session_id>" >&2
  exit 1
fi

SESSION_ID="$1"
SESSION_DIR="/tmp/karen_guard_${SESSION_ID}"

if [ ! -d "$SESSION_DIR" ]; then
  echo "Error: Session directory $SESSION_DIR does not exist." >&2
  exit 1
fi

HOST_USER=$(whoami)
HOST_UID=$(id -u)
HOST_GID=$(id -g)
USER_HOME=$(getent passwd "$HOST_USER" | cut -d: -f6)

if [ "$CONTAINER_ENGINE" = "podman" ]; then
  if ! podman image exists karen_guard; then
    echo "Building Karen Guard Podman image for user ${HOST_USER} (UID ${HOST_UID})..." >&2
    podman build -t karen_guard \
      --build-arg USERNAME="${HOST_USER}" \
      --build-arg USER_ID="${HOST_UID}" . >&2 || { echo "Error: Podman build failed." >&2; exit 1; }
  else
    echo "Karen Guard Podman image already exists, skipping build." >&2
  fi
else
  if ! docker image inspect karen_guard >/dev/null 2>&1; then
    echo "Building Karen Guard docker image for user ${HOST_USER} (UID ${HOST_UID})..." >&2
    docker build -t karen_guard \
      --build-arg USERNAME="${HOST_USER}" \
      --build-arg USER_ID="${HOST_UID}" . >&2 || { echo "Error: Docker build failed." >&2; exit 1; }
  else
    echo "Karen Guard docker image already exists, skipping build." >&2
  fi
fi

SESSION_GEMINI_DIR="${SESSION_DIR}/.gemini"
mkdir -p "${SESSION_GEMINI_DIR}/config"

echo "Preparing isolated Antigravity CLI environment..." >&2
if [ -d "${HOME}/.gemini" ]; then
    cp -R "${HOME}/.gemini/." "${SESSION_GEMINI_DIR}/" 2>/dev/null || true
    rm -rf "${SESSION_GEMINI_DIR}/brain"
fi

cat << 'EOF' > "${SESSION_GEMINI_DIR}/config/config.json"
{
  "userSettings": {
    "globalPermissionGrants": {
      "allow": [
        "unsandboxed(bash)",
        "unsandboxed(sh)",
        "command(*)",
        "read_file(*)",
        "write_file(*)",
        "read_url(*)",
        "mcp(*)"
      ],
      "deny": [
        "command(rm)",
        "command(rm -rf)",
        "write_file(/etc)"
      ]
    },
    "useAiCredits": false
  }
}
EOF

chown -R "${HOST_UID}:${HOST_GID}" "${SESSION_GEMINI_DIR}"

echo "Checking Antigravity CLI authentication..." >&2
if [ "$CONTAINER_ENGINE" = "podman" ]; then
  if podman run --rm --userns=keep-id -v "${SESSION_GEMINI_DIR}:${USER_HOME}/.gemini:z" \
      karen_guard agy models 2>&1 | grep -q -E "Error|Authentication|sign in"; then
      
      echo "Antigravity CLI is not authenticated. Starting interactive login flow..." >&2
      podman run -it --rm --userns=keep-id \
        -v "${SESSION_GEMINI_DIR}:${USER_HOME}/.gemini:z" \
        karen_guard agy
        
      echo "Login efetuado! Retomando execução do avaliador..." >&2
      cp -R "${SESSION_GEMINI_DIR}/"* "${USER_HOME}/.gemini/" 2>/dev/null || true
  fi
else
  if docker run --rm -v "${SESSION_GEMINI_DIR}:${USER_HOME}/.gemini" \
      karen_guard su - "${HOST_USER}" -c "agy models" 2>&1 | grep -q -E "Error|Authentication|sign in"; then
      
      echo "Antigravity CLI is not authenticated. Starting interactive login flow..." >&2
      docker run -it --rm \
        -v "${SESSION_GEMINI_DIR}:${USER_HOME}/.gemini" \
        karen_guard su - "${HOST_USER}" -c "agy"
        
      echo "Login efetuado! Retomando execução do avaliador..." >&2
      cp -R "${SESSION_GEMINI_DIR}/"* "${USER_HOME}/.gemini/" 2>/dev/null || true
  fi
fi

echo "Starting Karen Guard evaluation process for session ${SESSION_ID}..." >&2

# Physical isolation: mount ONLY what Karen needs to see, never the whole session
# directory. anti_karen/ is therefore not present inside the container at all — Bill's
# draft notes and a blind who_are_u.md are physically out of reach, not merely forbidden
# by a prompt instruction. docs/ and repos/ are read-only; out/ is Karen's only writable path.
mkdir -p "${SESSION_DIR}/out" "${SESSION_DIR}/docs" "${SESSION_DIR}/repos"
[ -f "${SESSION_DIR}/company_info.md" ] || touch "${SESSION_DIR}/company_info.md"

if [ "$CONTAINER_ENGINE" = "podman" ]; then
  podman run --rm --userns=keep-id \
    -v "${SESSION_DIR}/docs:/app/session/docs:ro,z" \
    -v "${SESSION_DIR}/repos:/app/session/repos:ro,z" \
    -v "${SESSION_DIR}/company_info.md:/app/session/company_info.md:ro,z" \
    -v "${SESSION_DIR}/out:/app/session/out:z" \
    -v "${SESSION_GEMINI_DIR}:${USER_HOME}/.gemini:z" \
    karen_guard run_evaluator
else
  docker run --rm \
    -v "${SESSION_DIR}/docs:/app/session/docs:ro" \
    -v "${SESSION_DIR}/repos:/app/session/repos:ro" \
    -v "${SESSION_DIR}/company_info.md:/app/session/company_info.md:ro" \
    -v "${SESSION_DIR}/out:/app/session/out" \
    -v "${SESSION_GEMINI_DIR}:${USER_HOME}/.gemini" \
    karen_guard su - "${HOST_USER}" -c "run_evaluator"
fi

if [ -f "${SESSION_DIR}/out/evaluation.md" ]; then
    mkdir -p "${SESSION_DIR}/anti_karen"
    mv "${SESSION_DIR}/out/evaluation.md" "${SESSION_DIR}/anti_karen/evaluation.md"
    cp "${SESSION_DIR}/anti_karen/evaluation.md" "${SESSION_DIR}/anti_karen/karen_output.md"
    cp "${SESSION_DIR}/anti_karen/evaluation.md" "${DIR}/../data/evaluation.md"
    echo "${SESSION_DIR}/anti_karen/karen_output.md"
else
    echo "Error: Karen did not produce out/evaluation.md. Check ${SESSION_DIR}/anti_karen/karen_run.err for details." >&2
    exit 1
fi