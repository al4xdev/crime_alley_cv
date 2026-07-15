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
    exec codex "${MODEL_ARGS[@]}" --add-dir /tmp "Read and execute the runbook at ${PROMPT_FILE}."
    ;;
  auth-check)
    exec codex login status
    ;;
  login)
    exec codex login --device-auth
    ;;
  evaluate)
    PROMPT_FILE="${1:?evaluate requires a prompt file}"
    OUTPUT_FILE="${2:?evaluate requires an output file}"
    TEMP_FILE="${OUTPUT_FILE}.tmp"
    rm -f "${TEMP_FILE}" "${OUTPUT_FILE}"
    codex exec --ephemeral --skip-git-repo-check "${MODEL_ARGS[@]}" \
      --sandbox read-only --ask-for-approval never \
      --output-last-message "${TEMP_FILE}" "$(cat "${PROMPT_FILE}")"
    test -s "${TEMP_FILE}"
    mv "${TEMP_FILE}" "${OUTPUT_FILE}"
    ;;
  *)
    echo "Error: unsupported Codex action: ${ACTION}" >&2
    exit 2
    ;;
esac
