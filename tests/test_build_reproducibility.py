from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTER_DOCKERFILE = REPOSITORY_ROOT / "Dockerfile"
KAREN_DOCKERFILE = REPOSITORY_ROOT / "karen_guard" / "Dockerfile"


def _dockerfile_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_container_inputs_are_content_addressed() -> None:
    outer = _dockerfile_text(OUTER_DOCKERFILE)
    karen = _dockerfile_text(KAREN_DOCKERFILE)

    python_image = re.search(r"^ARG PYTHON_IMAGE=(.+)$", outer, re.MULTILINE)
    karen_python_image = re.search(r"^ARG PYTHON_IMAGE=(.+)$", karen, re.MULTILINE)
    uv_image = re.search(r"^ARG UV_IMAGE=(.+)$", outer, re.MULTILINE)

    assert python_image is not None
    assert karen_python_image is not None
    assert uv_image is not None
    assert "@sha256:" in python_image.group(1)
    assert karen_python_image.group(1) == python_image.group(1)
    assert "ghcr.io/astral-sh/uv:0.11.28@sha256:" in uv_image.group(1)


def test_system_packages_use_an_immutable_snapshot() -> None:
    outer = _dockerfile_text(OUTER_DOCKERFILE)
    karen = _dockerfile_text(KAREN_DOCKERFILE)
    snapshot_script = (
        REPOSITORY_ROOT / "tools" / "configure_apt_snapshot.sh"
    ).read_text(encoding="utf-8")

    assert "ARG DEBIAN_SNAPSHOT=20260714T000000Z" in outer
    assert karen.count("ARG DEBIAN_SNAPSHOT=20260714T000000Z") == 2
    assert "snapshot.debian.org/archive/debian/" in snapshot_script
    assert "snapshot.debian.org/archive/debian-security/" in snapshot_script


def test_agy_archive_is_versioned_and_checksum_verified() -> None:
    outer = _dockerfile_text(OUTER_DOCKERFILE)
    karen = _dockerfile_text(KAREN_DOCKERFILE)
    installer = (REPOSITORY_ROOT / "tools" / "install_agy.sh").read_text(
        encoding="utf-8"
    )

    for dockerfile in (outer, karen):
        assert "ARG AGY_VERSION=1.1.2" in dockerfile
        assert "ARG AGY_RELEASE_ID=5174998495789056" in dockerfile
        assert "antigravity.google/cli/install.sh" not in dockerfile

    assert "sha512sum -c -" in installer
    assert "amd64)" in installer
    assert "arm64)" in installer
    assert len(re.search(r"ARG AGY_SHA512_AMD64=([0-9a-f]+)", outer).group(1)) == 128
    assert len(re.search(r"ARG AGY_SHA512_ARM64=([0-9a-f]+)", outer).group(1)) == 128


def test_karen_image_has_no_unused_python_sdk_install() -> None:
    karen = _dockerfile_text(KAREN_DOCKERFILE)

    assert "requirements.txt" not in karen
    assert "pip install" not in karen
    assert not (REPOSITORY_ROOT / "karen_guard" / "requirements.txt").exists()
