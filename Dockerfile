ARG PYTHON_IMAGE=python:3.13.14-slim-trixie@sha256:bffeb7bd6a85767587059c6ba23e1e9122078e3aa3fa836099171b9bb5a9bb00
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa

FROM ${UV_IMAGE} AS uv
FROM ${PYTHON_IMAGE}

ARG DEBIAN_SNAPSHOT=20260714T000000Z
ARG AGY_VERSION=1.1.2
ARG AGY_RELEASE_ID=5174998495789056
ARG AGY_SHA512_AMD64=b7a1b606a61c97ccb1592a64d689ad0fd0ed4491592f3474adf6cf0e6193d23b390e1308f89a1dd4e78306aeab13fe08dcb1a4a24da3e4583c3bd6845d52c456
ARG AGY_SHA512_ARM64=df2d147cee4f6d85630c98bcbc097369d47897b9aac97cbb6027b1e11c920c36a8de27f49cde05c3bbed0a9b9a1dfc2542e5b8c93606935ac4af7eb3cbad88b3
ARG CLAUDE_VERSION=2.1.210
ARG CLAUDE_SHA256_AMD64=e7d2ceb53ed4c2ced1fe7fc1c6331c98dc5f7b4c9b2722d9c5fa3dd5dff6f719
ARG CLAUDE_SHA256_ARM64=84feb193c1d91f3b5eba836ed47c0e4dee953195abba950917c3e101eff174e8
ARG CODEX_VERSION=0.144.4
ARG CODEX_SHA256_AMD64=37c985be9d89e8c4f43b3aa0594c1213eac212d30ae2b95221f08fec807515d1
ARG CODEX_SHA256_ARM64=4d07243ef4ae6786b8b321d7aea3f9be4e1d2c597ae5407e7c1b9873334082b2

COPY tools/configure_apt_snapshot.sh /usr/local/sbin/configure_apt_snapshot
RUN DEBIAN_SNAPSHOT="${DEBIAN_SNAPSHOT}" sh /usr/local/sbin/configure_apt_snapshot

# Install system dependencies including podman, fish shell, and tree
RUN apt-get update && apt-get install -y --no-install-recommends \
    podman \
    nftables \
    git \
    curl \
    ca-certificates \
    jq \
    fish \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Install the pinned uv binary from its content-addressed official image.
COPY --from=uv /uv /uvx /usr/local/bin/

# Install the pinned Antigravity CLI archive after verifying its published SHA-512.
COPY tools/install_agy.sh /usr/local/sbin/install_agy
RUN AGY_VERSION="${AGY_VERSION}" \
    AGY_RELEASE_ID="${AGY_RELEASE_ID}" \
    AGY_SHA512_AMD64="${AGY_SHA512_AMD64}" \
    AGY_SHA512_ARM64="${AGY_SHA512_ARM64}" \
    sh /usr/local/sbin/install_agy /usr/local/bin/agy

# Install pinned Claude Code and Codex binaries after verifying their official SHA-256 digests.
COPY tools/install_claude.sh /usr/local/sbin/install_claude
RUN CLAUDE_VERSION="${CLAUDE_VERSION}" \
    CLAUDE_SHA256_AMD64="${CLAUDE_SHA256_AMD64}" \
    CLAUDE_SHA256_ARM64="${CLAUDE_SHA256_ARM64}" \
    sh /usr/local/sbin/install_claude /usr/local/bin/claude

COPY tools/install_codex.sh /usr/local/sbin/install_codex
RUN CODEX_VERSION="${CODEX_VERSION}" \
    CODEX_SHA256_AMD64="${CODEX_SHA256_AMD64}" \
    CODEX_SHA256_ARM64="${CODEX_SHA256_ARM64}" \
    sh /usr/local/sbin/install_codex /usr/local/bin/codex

# Set up Podman configurations for nested container environment
RUN mkdir -p /etc/containers && \
    printf '[storage]\ndriver = "vfs"\nrunroot = "/run/containers/storage"\ngraphroot = "/var/lib/containers/storage"\n' > /etc/containers/storage.conf && \
    printf '[network]\nfirewall_driver = "iptables"\n' > /etc/containers/containers.conf

# Set up working directory
WORKDIR /app

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Sync dependencies (creates .venv)
RUN uv sync --frozen --dev

# Copy project files
COPY . .

# Set the credential-copying entrypoint.
RUN chmod +x entrypoint.sh config/agents/agent.sh config/agents/*/setup.sh \
    config/agents/*/run.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Default shell
CMD ["/usr/bin/fish"]
