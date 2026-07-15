#!/bin/bash
# entrypoint.sh — Start background services and execute container command
set -e

# Never give the outer container a writable bind mount to host credentials. The orchestrator and
# Karen setup operate on this ephemeral copy, which disappears with the container.
if [ -d /run/host-gemini ]; then
  mkdir -p /root/.gemini
  cp -a /run/host-gemini/. /root/.gemini/
  chmod 0700 /root/.gemini
fi

# Execute the main container command (CMD)
exec "$@"
