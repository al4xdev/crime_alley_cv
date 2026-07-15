ARG PYTHON_IMAGE=python:3.13.14-slim-trixie@sha256:bffeb7bd6a85767587059c6ba23e1e9122078e3aa3fa836099171b9bb5a9bb00
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa
ARG AGENT_PROVIDER=codex

FROM ${PYTHON_IMAGE} AS downloader
ARG DEBIAN_SNAPSHOT=20260714T000000Z
COPY tools/configure_apt_snapshot.sh /usr/local/sbin/configure_apt_snapshot
RUN DEBIAN_SNAPSHOT="${DEBIAN_SNAPSHOT}" sh /usr/local/sbin/configure_apt_snapshot
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* && mkdir -p /agent/bin

FROM downloader AS claude-installer
ARG CLAUDE_VERSION=2.1.210
ARG CLAUDE_SHA256_AMD64=e7d2ceb53ed4c2ced1fe7fc1c6331c98dc5f7b4c9b2722d9c5fa3dd5dff6f719
ARG CLAUDE_SHA256_ARM64=84feb193c1d91f3b5eba836ed47c0e4dee953195abba950917c3e101eff174e8
COPY tools/install_claude.sh /usr/local/sbin/install_agent
RUN CLAUDE_VERSION="${CLAUDE_VERSION}" CLAUDE_SHA256_AMD64="${CLAUDE_SHA256_AMD64}" \
    CLAUDE_SHA256_ARM64="${CLAUDE_SHA256_ARM64}" \
    sh /usr/local/sbin/install_agent /agent/bin/agent-cli

FROM downloader AS codex-installer
ARG CODEX_VERSION=0.144.4
ARG CODEX_SHA256_AMD64=37c985be9d89e8c4f43b3aa0594c1213eac212d30ae2b95221f08fec807515d1
ARG CODEX_SHA256_ARM64=4d07243ef4ae6786b8b321d7aea3f9be4e1d2c597ae5407e7c1b9873334082b2
COPY tools/install_codex.sh /usr/local/sbin/install_agent
RUN CODEX_VERSION="${CODEX_VERSION}" CODEX_SHA256_AMD64="${CODEX_SHA256_AMD64}" \
    CODEX_SHA256_ARM64="${CODEX_SHA256_ARM64}" \
    sh /usr/local/sbin/install_agent /agent/bin/agent-cli

FROM ${AGENT_PROVIDER}-installer AS selected-agent
FROM ${UV_IMAGE} AS uv
FROM ${PYTHON_IMAGE}

ARG AGENT_PROVIDER=codex
ARG DEBIAN_SNAPSHOT=20260714T000000Z
ARG USER_ID=1000
ARG GROUP_ID=1000
COPY tools/configure_apt_snapshot.sh /usr/local/sbin/configure_apt_snapshot
RUN DEBIAN_SNAPSHOT="${DEBIAN_SNAPSHOT}" sh /usr/local/sbin/configure_apt_snapshot \
    && apt-get update \
    && apt-get install -y --no-install-recommends bubblewrap \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid "${GROUP_ID}" celestial \
    && useradd --uid "${USER_ID}" --gid "${GROUP_ID}" --create-home celestial
COPY --from=uv /uv /uvx /usr/local/bin/
COPY --from=selected-agent /agent/bin/agent-cli /usr/local/bin/agent-cli
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY the_celestial /app/the_celestial
RUN case "${AGENT_PROVIDER}" in \
      claude) ln -s /usr/local/bin/agent-cli /usr/local/bin/claude ;; \
      codex) ln -s /usr/local/bin/agent-cli /usr/local/bin/codex ;; \
      *) exit 2 ;; \
    esac \
    && chmod 0755 /app/the_celestial/entrypoint.sh \
    && chown -R "${USER_ID}:${GROUP_ID}" /app /home/celestial
ENV AGENT_PROVIDER=${AGENT_PROVIDER}
ENV HOME=/home/celestial
ENV PATH=/app/.venv/bin:/usr/local/bin:/usr/bin:/bin
ENV DISABLE_AUTOUPDATER=1
ENV PYTHONDONTWRITEBYTECODE=1
USER ${USER_ID}:${GROUP_ID}
ENTRYPOINT ["/app/the_celestial/entrypoint.sh"]
