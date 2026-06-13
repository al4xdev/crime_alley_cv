FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g. git, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Default command is bash to allow interactive authentication exploration
CMD ["/bin/bash"]
