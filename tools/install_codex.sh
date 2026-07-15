#!/bin/sh
set -eu

: "${CODEX_VERSION:?CODEX_VERSION is required}"
: "${CODEX_SHA256_AMD64:?CODEX_SHA256_AMD64 is required}"
: "${CODEX_SHA256_ARM64:?CODEX_SHA256_ARM64 is required}"

destination="${1:-/usr/local/bin/codex}"
architecture="$(dpkg --print-architecture)"

case "${architecture}" in
  amd64)
    platform=x86_64-unknown-linux-musl
    checksum="${CODEX_SHA256_AMD64}"
    ;;
  arm64)
    platform=aarch64-unknown-linux-musl
    checksum="${CODEX_SHA256_ARM64}"
    ;;
  *)
    printf 'Unsupported Codex architecture: %s\n' "${architecture}" >&2
    exit 1
    ;;
esac

temporary_directory="$(mktemp -d)"
trap 'rm -rf "${temporary_directory}"' EXIT
archive="${temporary_directory}/codex.tar.gz"
url="https://github.com/openai/codex/releases/download/rust-v${CODEX_VERSION}/codex-${platform}.tar.gz"

curl -fsSL "${url}" -o "${archive}"
printf '%s  %s\n' "${checksum}" "${archive}" | sha256sum -c -
tar -xzf "${archive}" -C "${temporary_directory}" "codex-${platform}"
install -m 0755 "${temporary_directory}/codex-${platform}" "${destination}"
