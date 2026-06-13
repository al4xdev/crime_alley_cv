#!/bin/bash
cd /app/session
exec agy --dangerously-skip-permissions --prompt "$(cat /app/prompt_persona.txt)"