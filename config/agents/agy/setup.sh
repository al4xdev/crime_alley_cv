#!/bin/bash
# config/agents/agy/setup.sh <session_dir> <runtime_uid> <runtime_gid> <user_home>
set -euo pipefail

SESSION_DIR="$1"
RUNTIME_UID="$2"
RUNTIME_GID="$3"

SESSION_GEMINI_DIR="${SESSION_DIR}/.gemini"
SESSION_AUTH_DIR="${SESSION_GEMINI_DIR}/antigravity-cli"
HOST_TOKEN="${HOME}/.gemini/antigravity-cli/antigravity-oauth-token"
SESSION_TOKEN="${SESSION_AUTH_DIR}/antigravity-oauth-token"

echo "Preparing minimal Antigravity authentication material..." >&2
mkdir -p "${SESSION_AUTH_DIR}"

if [ -f "${HOST_TOKEN}" ] && [ ! -f "${SESSION_TOKEN}" ]; then
    install -m 0600 "${HOST_TOKEN}" "${SESSION_TOKEN}"
fi

chown -R "${RUNTIME_UID}:${RUNTIME_GID}" "${SESSION_GEMINI_DIR}"
