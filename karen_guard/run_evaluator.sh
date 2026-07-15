#!/bin/bash
set -euo pipefail

cd /app/session

exec agy \
  --sandbox \
  --mode accept-edits \
  --log-file /tmp/agy.log \
  --prompt "$(cat /app/prompt_persona.txt)"
