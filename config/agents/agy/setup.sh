#!/bin/bash
# config/agents/agy/setup.sh <session_dir> <host_uid> <host_gid> <user_home>
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

SESSION_DIR="$1"
HOST_UID="$2"
HOST_GID="$3"
USER_HOME="$4"

SESSION_GEMINI_DIR="${SESSION_DIR}/.gemini"
mkdir -p "${SESSION_GEMINI_DIR}/config"

echo "Preparing isolated Antigravity CLI environment..." >&2
if [ -d "${HOME}/.gemini" ]; then
    cp -R "${HOME}/.gemini/." "${SESSION_GEMINI_DIR}/" 2>/dev/null || true
    rm -rf "${SESSION_GEMINI_DIR}/brain"
fi

# Ensure workspace trust for /app and /app/session in the isolated settings
SETTINGS_FILE="${SESSION_GEMINI_DIR}/antigravity-cli/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    if TMP_SETTINGS=$(jq '.trustedWorkspaces = ((.trustedWorkspaces // []) + ["/app", "/app/session"] | unique)' "$SETTINGS_FILE" 2>/dev/null); then
        echo "$TMP_SETTINGS" > "$SETTINGS_FILE"
    fi
else
    mkdir -p "$(dirname "$SETTINGS_FILE")"
    cat << 'EOF' > "$SETTINGS_FILE"
{
  "allowNonWorkspaceAccess": true,
  "trustedWorkspaces": [
    "/app",
    "/app/session"
  ]
}
EOF
fi

cp "$DIR/config/config.json" "${SESSION_GEMINI_DIR}/config/config.json"
cp "$DIR/config/AGENTS.md" "${SESSION_GEMINI_DIR}/config/AGENTS.md"

chown -R "${HOST_UID}:${HOST_GID}" "${SESSION_GEMINI_DIR}"
