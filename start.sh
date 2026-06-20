#!/bin/bash
# start.sh — Launch the entire Crime Alley CV pipeline inside a Docker container (with Podman inside)

IMAGE_NAME="crime_alley_pipeline"

# Determine the correct docker command (with or without sudo)
if docker ps >/dev/null 2>&1; then
  DOCKER_CMD="docker"
elif command -v sudo >/dev/null 2>&1; then
  echo "Docker permission denied. Trying with sudo..." >&2
  DOCKER_CMD="sudo docker"
else
  echo "Error: Docker is not accessible, and sudo is not available." >&2
  exit 1
fi

# Determine the correct user home directory to mount the .gemini tokens
if [ -n "$SUDO_USER" ]; then
  ORIG_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
  ORIG_HOME="$HOME"
fi

# 1. Build the global orchestrator image
echo "Building global orchestrator image..." >&2
$DOCKER_CMD build -t "$IMAGE_NAME" . || { echo "Error: Docker build failed." >&2; exit 1; }

# 2. Prepare persistent data directories on the host
mkdir -p .data/docs
mkdir -p .runs

# 3. Launch the container interactively
# We mount:
# - .data/ to persist inputs (cv.md, job.md, who_are_u.md) and outputs (action_plan.md)
# - .runs/ to persist historical logs
# - ~/.gemini to share credentials from host
# We run with --privileged so that Podman can run inside the Docker container
echo "Starting pipeline container in interactive mode (using fish shell)..." >&2
$DOCKER_CMD run -it --privileged --rm \
  -v "$(pwd)/.data:/app/.data" \
  -v "$(pwd)/.runs:/app/.runs" \
  -v "$ORIG_HOME/.gemini:/root/.gemini" \
  "$IMAGE_NAME"
