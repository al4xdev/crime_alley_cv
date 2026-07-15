#!/bin/sh
set -eu

: "${DEBIAN_SNAPSHOT:?DEBIAN_SNAPSHOT is required}"

sources=/etc/apt/sources.list.d/debian.sources
keyring=/usr/share/keyrings/debian-archive-keyring.gpg

printf '%s\n' \
  'Types: deb' \
  "URIs: https://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}/" \
  'Suites: trixie trixie-updates' \
  'Components: main' \
  "Signed-By: ${keyring}" \
  '' \
  'Types: deb' \
  "URIs: https://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT}/" \
  'Suites: trixie-security' \
  'Components: main' \
  "Signed-By: ${keyring}" \
  > "${sources}"

printf '%s\n' \
  'Acquire::Check-Valid-Until "false";' \
  'Acquire::Retries "3";' \
  > /etc/apt/apt.conf.d/99snapshot
