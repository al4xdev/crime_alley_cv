#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

if ! docker ps >/dev/null 2>&1; then
  echo "No permission to access Docker socket. Retrying command via 'sg docker'..." >&2
  exec sg docker -c "$0 $*"
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

echo "Building Karen Guard docker image for user ${HOST_USER} (UID ${HOST_UID})..." >&2
docker build -t karen_guard \
  --build-arg USERNAME="${HOST_USER}" \
  --build-arg USER_ID="${HOST_UID}" . >&2

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
        "read_url(*)"
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

chown -R "${HOST_UID}:${HOST_UID}" "${SESSION_GEMINI_DIR}"

echo "Checking Antigravity CLI authentication..." >&2
if docker run --rm -v "${SESSION_GEMINI_DIR}:/home/${HOST_USER}/.gemini" \
    karen_guard su - "${HOST_USER}" -c "agy models" 2>&1 | grep -q -E "Error|Authentication|sign in"; then
    
    echo "Antigravity CLI is not authenticated. Starting interactive login flow..." >&2
    docker run -it --rm \
      -v "${SESSION_GEMINI_DIR}:/home/${HOST_USER}/.gemini" \
      karen_guard su - "${HOST_USER}" -c "agy"
      
    echo "Login efetuado! Retomando execução do avaliador..." >&2
    cp -R "${SESSION_GEMINI_DIR}/"* "${HOME}/.gemini/" 2>/dev/null || true
fi

echo "Starting Karen Guard evaluation process for session ${SESSION_ID}..." >&2
docker run -it --rm \
  -v "${SESSION_DIR}:/app/session" \
  -v "${SESSION_GEMINI_DIR}:/home/${HOST_USER}/.gemini" \
  karen_guard su - "${HOST_USER}" -c "run_evaluator"

if [ -f "${SESSION_DIR}/evaluation.md" ]; then
    cp "${SESSION_DIR}/evaluation.md" "${SESSION_DIR}/karen_output.md"
    cp "${SESSION_DIR}/evaluation.md" "${DIR}/../data/evaluation.md"
    echo "${SESSION_DIR}/karen_output.md"
fi