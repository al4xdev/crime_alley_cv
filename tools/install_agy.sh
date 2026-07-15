#!/bin/sh
set -eu

: "${AGY_VERSION:?AGY_VERSION is required}"
: "${AGY_RELEASE_ID:?AGY_RELEASE_ID is required}"
: "${AGY_SHA512_AMD64:?AGY_SHA512_AMD64 is required}"
: "${AGY_SHA512_ARM64:?AGY_SHA512_ARM64 is required}"

destination="${1:-/usr/local/bin/agy}"
architecture="$(dpkg --print-architecture)"

case "${architecture}" in
  amd64)
    platform=linux-x64
    archive_name=cli_linux_x64.tar.gz
    checksum="${AGY_SHA512_AMD64}"
    ;;
  arm64)
    platform=linux-arm
    archive_name=cli_linux_arm64.tar.gz
    checksum="${AGY_SHA512_ARM64}"
    ;;
  *)
    printf 'Unsupported agy architecture: %s\n' "${architecture}" >&2
    exit 1
    ;;
esac

temporary_directory="$(mktemp -d)"
trap 'rm -rf "${temporary_directory}"' EXIT
archive="${temporary_directory}/${archive_name}"
url="https://storage.googleapis.com/antigravity-public/antigravity-cli/${AGY_VERSION}-${AGY_RELEASE_ID}/${platform}/${archive_name}"

curl -fsSL "${url}" -o "${archive}"
printf '%s  %s\n' "${checksum}" "${archive}" | sha512sum -c -
tar -xzf "${archive}" -C "${temporary_directory}" antigravity
install -m 0755 "${temporary_directory}/antigravity" "${destination}"
