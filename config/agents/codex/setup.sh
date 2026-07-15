#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCOPE="$1"
WORKSPACE="$2"
RUNTIME_UID="$3"
RUNTIME_GID="$4"
USER_HOME="$5"

if [ "${SCOPE}" = "outer" ]; then
  CODEX_HOME_PATH="${USER_HOME}/.codex"
  HOST_CREDENTIAL="/run/host-agent-auth"
elif [ "${SCOPE}" = "evaluator" ]; then
  CODEX_HOME_PATH="${WORKSPACE}/.codex"
  HOST_CREDENTIAL="${HOME}/.codex/auth.json"
else
  echo "Error: unsupported setup scope: ${SCOPE}" >&2
  exit 2
fi

mkdir -p "${CODEX_HOME_PATH}"
if [ -f "${HOST_CREDENTIAL}" ] && [ ! -f "${CODEX_HOME_PATH}/auth.json" ]; then
  install -m 0600 "${HOST_CREDENTIAL}" "${CODEX_HOME_PATH}/auth.json"
fi
install -m 0644 "${DIR}/config/AGENTS.md" "${CODEX_HOME_PATH}/AGENTS.md"
if [ "${SCOPE}" = "evaluator" ]; then
  install -m 0644 "${DIR}/config/config.toml" "${CODEX_HOME_PATH}/config.toml"
fi
chown -R "${RUNTIME_UID}:${RUNTIME_GID}" "${CODEX_HOME_PATH}"
