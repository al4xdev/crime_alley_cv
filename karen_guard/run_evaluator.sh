#!/bin/bash
set -euo pipefail

cd /app/session

exec /opt/agents/agent.sh "${AGENT_PROVIDER:?AGENT_PROVIDER is required}" \
  evaluate /app/prompt_persona.txt /app/session/out/evaluation.md
