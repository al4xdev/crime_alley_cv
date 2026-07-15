#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCOPE="$1"
WORKSPACE="$2"
RUNTIME_UID="$3"
RUNTIME_GID="$4"
USER_HOME="$5"

if [ "${SCOPE}" = "outer" ]; then
  CLAUDE_HOME="${USER_HOME}/.claude"
  HOST_CREDENTIAL="/run/host-agent-auth"
elif [ "${SCOPE}" = "evaluator" ]; then
  CLAUDE_HOME="${WORKSPACE}/.claude"
  HOST_CREDENTIAL="${HOME}/.claude/.credentials.json"
else
  echo "Error: unsupported setup scope: ${SCOPE}" >&2
  exit 2
fi

mkdir -p "${CLAUDE_HOME}"
if [ -f "${HOST_CREDENTIAL}" ] && [ ! -f "${CLAUDE_HOME}/.credentials.json" ]; then
  install -m 0600 "${HOST_CREDENTIAL}" "${CLAUDE_HOME}/.credentials.json"
fi
install -m 0644 "${DIR}/config/CLAUDE.md" "${CLAUDE_HOME}/CLAUDE.md"
if [ "${SCOPE}" = "evaluator" ]; then
  install -m 0644 "${DIR}/config/settings.json" "${CLAUDE_HOME}/settings.json"
fi
chown -R "${RUNTIME_UID}:${RUNTIME_GID}" "${CLAUDE_HOME}"
