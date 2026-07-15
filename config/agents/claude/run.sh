#!/bin/bash
set -euo pipefail

ACTION="${1:-}"
shift || true
export DISABLE_AUTOUPDATER=1
MODEL_ARGS=()
if [ -n "${AGENT_MODEL:-}" ]; then
  MODEL_ARGS=(--model "${AGENT_MODEL}")
fi

case "${ACTION}" in
  interactive)
    PROMPT_FILE="${1:?interactive requires a prompt file}"
    exec claude "${MODEL_ARGS[@]}" --add-dir /tmp "$(cat "${PROMPT_FILE}")"
    ;;
  auth-check)
    exec claude auth status
    ;;
  login)
    exec claude auth login
    ;;
  evaluate)
    PROMPT_FILE="${1:?evaluate requires a prompt file}"
    OUTPUT_FILE="${2:?evaluate requires an output file}"
    TEMP_FILE="${OUTPUT_FILE}.tmp"
    rm -f "${TEMP_FILE}" "${OUTPUT_FILE}"
    claude -p "${MODEL_ARGS[@]}" --output-format text --permission-mode dontAsk \
      --allowedTools Read Glob Grep \
      --disallowedTools Bash Edit Write NotebookEdit WebFetch WebSearch Agent \
      "$(cat "${PROMPT_FILE}")" > "${TEMP_FILE}"
    test -s "${TEMP_FILE}"
    mv "${TEMP_FILE}" "${OUTPUT_FILE}"
    ;;
  *)
    echo "Error: unsupported Claude action: ${ACTION}" >&2
    exit 2
    ;;
esac
