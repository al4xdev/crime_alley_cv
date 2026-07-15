#!/bin/bash
# entrypoint.sh — Start background services and execute container command
set -e

# The selected adapter receives one read-only host credential and copies it into
# ephemeral container storage. Other providers' credentials are never mounted.
if [ -n "${AGENT_PROVIDER:-}" ]; then
  /app/config/agents/agent.sh "${AGENT_PROVIDER}" setup outer /app 0 0 /root
fi

# Execute the main container command (CMD)
exec "$@"
