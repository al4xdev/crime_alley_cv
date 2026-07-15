#!/bin/bash
set -euo pipefail

ACTION="${1:-}"
shift || true
MODEL_ARGS=()
if [ -n "${AGENT_MODEL:-}" ]; then
  MODEL_ARGS=(--model "${AGENT_MODEL}")
fi

case "${ACTION}" in
  interactive)
    PROMPT_FILE="${1:?interactive requires a prompt file}"
    exec agy "${MODEL_ARGS[@]}" --prompt "$(cat "${PROMPT_FILE}")"
    ;;
  auth-check)
    exec agy models
    ;;
  login)
    exec agy
    ;;
  evaluate)
    PROMPT_FILE="${1:?evaluate requires a prompt file}"
    OUTPUT_FILE="${2:?evaluate requires an output file}"
    rm -f "${OUTPUT_FILE}"
    agy "${MODEL_ARGS[@]}" --sandbox --mode accept-edits --log-file /tmp/agy.log \
      --prompt "$(cat "${PROMPT_FILE}")"
    test -s "${OUTPUT_FILE}"
    ;;
  *)
    echo "Error: unsupported agy action: ${ACTION}" >&2
    exit 2
    ;;
esac
