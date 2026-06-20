FROM python:3.13-slim

# Install system dependencies including podman, fish shell, and tree
RUN apt-get update && apt-get install -y --no-install-recommends \
    podman \
    nftables \
    git \
    curl \
    ca-certificates \
    jq \
    at \
    sudo \
    fish \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -fsSL https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

# Install Antigravity CLI (agy)
RUN curl -fsSL https://antigravity.google/cli/install.sh | bash && \
    mv /root/.local/bin/agy /usr/local/bin/agy

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

# Set entrypoint to run atd daemon
RUN chmod +x entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Default shell
CMD ["/usr/bin/fish"]
