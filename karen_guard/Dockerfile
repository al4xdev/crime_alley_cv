FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    sudo \
    jq \
    && rm -rf /var/lib/apt/lists/*

ARG USERNAME=karen
ARG USER_ID=1000

RUN if [ "${USER_ID}" -ne 0 ] && [ "${USERNAME}" != "root" ]; then \
        if ! getent group "${USER_ID}" >/dev/null 2>&1; then \
            groupadd -g ${USER_ID} ${USERNAME}; \
        fi && \
        if ! getent passwd "${USER_ID}" >/dev/null 2>&1 && ! getent passwd "${USERNAME}" >/dev/null 2>&1; then \
            useradd -u ${USER_ID} -g ${USER_ID} -m -s /bin/bash ${USERNAME}; \
        fi && \
        echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers; \
    fi && \
    chown -R ${USER_ID}:${USER_ID} /app

RUN pip install --no-cache-dir uv

# Instalação do agy
RUN curl -fsSL https://antigravity.google/cli/install.sh | bash && \
    mv /root/.local/bin/agy /usr/local/bin/agy

ENV PATH="/usr/local/bin:${PATH}"

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY prompt_persona.txt /app/prompt_persona.txt
COPY run_evaluator.sh /usr/local/bin/run_evaluator
RUN chmod +x /usr/local/bin/run_evaluator

CMD ["/bin/bash"]