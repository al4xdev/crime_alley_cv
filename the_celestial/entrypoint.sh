#!/bin/sh
set -eu

case "${AGENT_PROVIDER}" in
  claude)
    mkdir -p "${HOME}/.claude"
    install -m 0600 /run/host-agent-auth "${HOME}/.claude/.credentials.json"
    ;;
  codex)
    mkdir -p "${HOME}/.codex"
    install -m 0600 /run/host-agent-auth "${HOME}/.codex/auth.json"
    ;;
  *)
    echo "Unsupported Celestial provider: ${AGENT_PROVIDER}" >&2
    exit 2
    ;;
esac

exec "$@"
