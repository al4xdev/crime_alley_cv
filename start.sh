#!/bin/bash
# start.sh — Launch the entire Crime Alley CV pipeline inside a Docker container (with Podman inside)

IMAGE_NAME="crime_alley_pipeline"

# 1. Build the global orchestrator image
echo "Building global orchestrator image..." >&2
docker build -t "$IMAGE_NAME" . || { echo "Error: Docker build failed." >&2; exit 1; }

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
docker run -it --privileged --rm \
  -v "$(pwd)/.data:/app/.data" \
  -v "$(pwd)/.runs:/app/.runs" \
  -v "$HOME/.gemini:/root/.gemini" \
  "$IMAGE_NAME"
