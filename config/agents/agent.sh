#!/bin/bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: agent.sh <agy|claude|codex> <setup|interactive|auth-check|login|evaluate> [...]" >&2
  exit 2
fi

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROVIDER="$1"
ACTION="$2"
shift 2

case "${PROVIDER}" in
  agy|claude|codex) ;;
  *)
    echo "Error: unsupported agent provider: ${PROVIDER}" >&2
    exit 2
    ;;
esac

case "${ACTION}" in
  setup)
    exec "${DIR}/${PROVIDER}/setup.sh" "$@"
    ;;
  interactive|auth-check|login|evaluate)
    exec "${DIR}/${PROVIDER}/run.sh" "${ACTION}" "$@"
    ;;
  *)
    echo "Error: unsupported agent action: ${ACTION}" >&2
    exit 2
    ;;
esac
