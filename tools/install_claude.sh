#!/bin/sh
set -eu

: "${CLAUDE_VERSION:?CLAUDE_VERSION is required}"
: "${CLAUDE_SHA256_AMD64:?CLAUDE_SHA256_AMD64 is required}"
: "${CLAUDE_SHA256_ARM64:?CLAUDE_SHA256_ARM64 is required}"

destination="${1:-/usr/local/bin/claude}"
architecture="$(dpkg --print-architecture)"

case "${architecture}" in
  amd64)
    platform=linux-x64
    checksum="${CLAUDE_SHA256_AMD64}"
    ;;
  arm64)
    platform=linux-arm64
    checksum="${CLAUDE_SHA256_ARM64}"
    ;;
  *)
    printf 'Unsupported Claude Code architecture: %s\n' "${architecture}" >&2
    exit 1
    ;;
esac

temporary_directory="$(mktemp -d)"
trap 'rm -rf "${temporary_directory}"' EXIT
binary="${temporary_directory}/claude"
url="https://downloads.claude.ai/claude-code-releases/${CLAUDE_VERSION}/${platform}/claude"

curl -fsSL "${url}" -o "${binary}"
printf '%s  %s\n' "${checksum}" "${binary}" | sha256sum -c -
install -m 0755 "${binary}" "${destination}"
