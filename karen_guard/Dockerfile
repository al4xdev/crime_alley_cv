ARG PYTHON_IMAGE=python:3.13.14-slim-trixie@sha256:bffeb7bd6a85767587059c6ba23e1e9122078e3aa3fa836099171b9bb5a9bb00

FROM ${PYTHON_IMAGE} AS agy-installer

ARG DEBIAN_SNAPSHOT=20260714T000000Z
ARG AGY_VERSION=1.1.2
ARG AGY_RELEASE_ID=5174998495789056
ARG AGY_SHA512_AMD64=b7a1b606a61c97ccb1592a64d689ad0fd0ed4491592f3474adf6cf0e6193d23b390e1308f89a1dd4e78306aeab13fe08dcb1a4a24da3e4583c3bd6845d52c456
ARG AGY_SHA512_ARM64=df2d147cee4f6d85630c98bcbc097369d47897b9aac97cbb6027b1e11c920c36a8de27f49cde05c3bbed0a9b9a1dfc2542e5b8c93606935ac4af7eb3cbad88b3

COPY tools/configure_apt_snapshot.sh /usr/local/sbin/configure_apt_snapshot
RUN DEBIAN_SNAPSHOT="${DEBIAN_SNAPSHOT}" sh /usr/local/sbin/configure_apt_snapshot

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY tools/install_agy.sh /usr/local/sbin/install_agy
RUN AGY_VERSION="${AGY_VERSION}" \
    AGY_RELEASE_ID="${AGY_RELEASE_ID}" \
    AGY_SHA512_AMD64="${AGY_SHA512_AMD64}" \
    AGY_SHA512_ARM64="${AGY_SHA512_ARM64}" \
    sh /usr/local/sbin/install_agy /usr/local/bin/agy


FROM ${PYTHON_IMAGE}

ARG USERNAME=karen
ARG USER_ID=1000
ARG GROUP_ID=1000
ARG DEBIAN_SNAPSHOT=20260714T000000Z

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

COPY --from=agy-installer /usr/local/bin/agy /usr/local/bin/agy

WORKDIR /app

COPY karen_guard/prompt_persona.txt /app/prompt_persona.txt
COPY karen_guard/run_evaluator.sh /usr/local/bin/run_evaluator
COPY config/agents/agy/config/config.json /home/${USERNAME}/.gemini/config/config.json

RUN mkdir -p /app/session/out /home/${USERNAME}/.gemini/antigravity-cli \
    && printf '%s\n' \
        '{' \
        '  "allowNonWorkspaceAccess": false,' \
        '  "trustedWorkspaces": ["/app/session"]' \
        '}' \
        > /home/${USERNAME}/.gemini/antigravity-cli/settings.json \
    && chmod 0755 /usr/local/bin/run_evaluator \
    && chown -R "${USER_ID}:${GROUP_ID}" /app /home/${USERNAME}

ENV HOME=/home/${USERNAME}
ENV PATH=/usr/local/bin:${PATH}

USER ${USER_ID}:${GROUP_ID}

CMD ["run_evaluator"]
