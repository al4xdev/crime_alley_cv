#!/bin/bash
# entrypoint.sh — Start background services and execute container command

# Start the atd daemon (job scheduler)
if [ -x /usr/sbin/atd ]; then
  /usr/sbin/atd
fi

# Execute the main container command (CMD)
exec "$@"
