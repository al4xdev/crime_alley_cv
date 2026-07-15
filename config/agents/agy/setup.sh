#!/bin/bash
# config/agents/agy/setup.sh <outer|evaluator> <workspace> <runtime_uid> <runtime_gid> <user_home>
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCOPE="$1"
WORKSPACE="$2"
RUNTIME_UID="$3"
RUNTIME_GID="$4"
USER_HOME="$5"

SESSION_GEMINI_DIR="${WORKSPACE}/.gemini"
SESSION_AUTH_DIR="${SESSION_GEMINI_DIR}/antigravity-cli"
SESSION_TOKEN="${SESSION_AUTH_DIR}/antigravity-oauth-token"
HOST_TOKEN="${HOME}/.gemini/antigravity-cli/antigravity-oauth-token"

if [ "${SCOPE}" = "outer" ]; then
    SESSION_GEMINI_DIR="${USER_HOME}/.gemini"
    SESSION_AUTH_DIR="${SESSION_GEMINI_DIR}/antigravity-cli"
    SESSION_TOKEN="${SESSION_AUTH_DIR}/antigravity-oauth-token"
    HOST_TOKEN="/run/host-agent-auth"
elif [ "${SCOPE}" != "evaluator" ]; then
    echo "Error: unsupported setup scope: ${SCOPE}" >&2
    exit 2
fi

echo "Preparing minimal Antigravity authentication material..." >&2
mkdir -p "${SESSION_AUTH_DIR}"

if [ -f "${HOST_TOKEN}" ] && [ ! -f "${SESSION_TOKEN}" ]; then
    install -m 0600 "${HOST_TOKEN}" "${SESSION_TOKEN}"
fi

mkdir -p "${SESSION_GEMINI_DIR}/config"
install -m 0644 "${DIR}/config/AGENTS.md" "${SESSION_GEMINI_DIR}/config/AGENTS.md"
if [ "${SCOPE}" = "evaluator" ]; then
    install -m 0644 "${DIR}/config/config.json" "${SESSION_GEMINI_DIR}/config/config.json"
fi

chown -R "${RUNTIME_UID}:${RUNTIME_GID}" "${SESSION_GEMINI_DIR}"
