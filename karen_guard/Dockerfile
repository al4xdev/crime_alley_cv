ARG PYTHON_IMAGE=python:3.13.14-slim-trixie@sha256:bffeb7bd6a85767587059c6ba23e1e9122078e3aa3fa836099171b9bb5a9bb00
ARG AGENT_PROVIDER=agy

FROM ${PYTHON_IMAGE} AS agent-downloader

ARG DEBIAN_SNAPSHOT=20260714T000000Z
COPY tools/configure_apt_snapshot.sh /usr/local/sbin/configure_apt_snapshot
RUN DEBIAN_SNAPSHOT="${DEBIAN_SNAPSHOT}" sh /usr/local/sbin/configure_apt_snapshot
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /agent/bin

FROM agent-downloader AS agy-installer
ARG AGY_VERSION=1.1.2
ARG AGY_RELEASE_ID=5174998495789056
ARG AGY_SHA512_AMD64=b7a1b606a61c97ccb1592a64d689ad0fd0ed4491592f3474adf6cf0e6193d23b390e1308f89a1dd4e78306aeab13fe08dcb1a4a24da3e4583c3bd6845d52c456
ARG AGY_SHA512_ARM64=df2d147cee4f6d85630c98bcbc097369d47897b9aac97cbb6027b1e11c920c36a8de27f49cde05c3bbed0a9b9a1dfc2542e5b8c93606935ac4af7eb3cbad88b3
COPY tools/install_agy.sh /usr/local/sbin/install_agent
RUN AGY_VERSION="${AGY_VERSION}" \
    AGY_RELEASE_ID="${AGY_RELEASE_ID}" \
    AGY_SHA512_AMD64="${AGY_SHA512_AMD64}" \
    AGY_SHA512_ARM64="${AGY_SHA512_ARM64}" \
    sh /usr/local/sbin/install_agent /agent/bin/agent-cli

FROM agent-downloader AS claude-installer
ARG CLAUDE_VERSION=2.1.210
ARG CLAUDE_SHA256_AMD64=e7d2ceb53ed4c2ced1fe7fc1c6331c98dc5f7b4c9b2722d9c5fa3dd5dff6f719
ARG CLAUDE_SHA256_ARM64=84feb193c1d91f3b5eba836ed47c0e4dee953195abba950917c3e101eff174e8
COPY tools/install_claude.sh /usr/local/sbin/install_agent
RUN CLAUDE_VERSION="${CLAUDE_VERSION}" \
    CLAUDE_SHA256_AMD64="${CLAUDE_SHA256_AMD64}" \
    CLAUDE_SHA256_ARM64="${CLAUDE_SHA256_ARM64}" \
    sh /usr/local/sbin/install_agent /agent/bin/agent-cli

FROM agent-downloader AS codex-installer
ARG CODEX_VERSION=0.144.4
ARG CODEX_SHA256_AMD64=37c985be9d89e8c4f43b3aa0594c1213eac212d30ae2b95221f08fec807515d1
ARG CODEX_SHA256_ARM64=4d07243ef4ae6786b8b321d7aea3f9be4e1d2c597ae5407e7c1b9873334082b2
COPY tools/install_codex.sh /usr/local/sbin/install_agent
RUN CODEX_VERSION="${CODEX_VERSION}" \
    CODEX_SHA256_AMD64="${CODEX_SHA256_AMD64}" \
    CODEX_SHA256_ARM64="${CODEX_SHA256_ARM64}" \
    sh /usr/local/sbin/install_agent /agent/bin/agent-cli

FROM ${AGENT_PROVIDER}-installer AS selected-agent

FROM ${PYTHON_IMAGE}

ARG USERNAME=karen
ARG USER_ID=1000
ARG GROUP_ID=1000
ARG DEBIAN_SNAPSHOT=20260714T000000Z
ARG AGENT_PROVIDER=agy

COPY tools/configure_apt_snapshot.sh /usr/local/sbin/configure_apt_snapshot
RUN DEBIAN_SNAPSHOT="${DEBIAN_SNAPSHOT}" sh /usr/local/sbin/configure_apt_snapshot

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    jq \
    && rm -rf /var/lib/apt/lists/* \
    && if ! getent group "${GROUP_ID}" >/dev/null; then \
        groupadd --gid "${GROUP_ID}" "${USERNAME}"; \
    fi \
    && useradd --uid "${USER_ID}" --gid "${GROUP_ID}" --create-home \
        --shell /bin/bash "${USERNAME}"

COPY --from=selected-agent /agent/bin/agent-cli /usr/local/bin/agent-cli

WORKDIR /app

COPY karen_guard/prompt_persona.txt /app/prompt_persona.txt
COPY karen_guard/run_evaluator.sh /usr/local/bin/run_evaluator
COPY config/agents /opt/agents

RUN case "${AGENT_PROVIDER}" in \
      agy) \
        ln -s /usr/local/bin/agent-cli /usr/local/bin/agy; \
        mkdir -p "/home/${USERNAME}/.gemini/config" "/home/${USERNAME}/.gemini/antigravity-cli"; \
        cp /opt/agents/agy/config/config.json "/home/${USERNAME}/.gemini/config/config.json"; \
        ;; \
      claude) \
        ln -s /usr/local/bin/agent-cli /usr/local/bin/claude; \
        mkdir -p "/home/${USERNAME}/.claude"; \
        cp /opt/agents/claude/config/CLAUDE.md /opt/agents/claude/config/settings.json "/home/${USERNAME}/.claude/"; \
        ;; \
      codex) \
        ln -s /usr/local/bin/agent-cli /usr/local/bin/codex; \
        mkdir -p "/home/${USERNAME}/.codex"; \
        cp /opt/agents/codex/config/AGENTS.md /opt/agents/codex/config/config.toml "/home/${USERNAME}/.codex/"; \
        ;; \
      *) echo "Unsupported AGENT_PROVIDER: ${AGENT_PROVIDER}" >&2; exit 1 ;; \
    esac \
    && chmod 0755 /usr/local/bin/run_evaluator /opt/agents/agent.sh /opt/agents/*/run.sh \
    && mkdir -p /app/session/out \
    && chown -R "${USER_ID}:${GROUP_ID}" /app /home/${USERNAME}

ENV AGENT_PROVIDER=${AGENT_PROVIDER}
ENV HOME=/home/${USERNAME}
ENV PATH=/usr/local/bin:${PATH}
ENV DISABLE_AUTOUPDATER=1
ENV CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

USER ${USER_ID}:${GROUP_ID}

CMD ["run_evaluator"]
