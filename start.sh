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

# 2. Prepare configurable persistent directories on the host. Their absolute host paths are
# mounted at stable locations in the outer container, where the pipeline receives matching roots.
DATA_HOST_DIR="${PIPELINE_DATA_DIR:-.data}"
RUNS_HOST_DIR="${PIPELINE_RUNS_DIR:-.runs}"
SESSION_CONTAINER_ROOT="${PIPELINE_SESSION_ROOT:-/tmp}"
mkdir -p "$DATA_HOST_DIR/docs" "$RUNS_HOST_DIR" || {
  echo "Error: Could not create pipeline data directories." >&2
  exit 1
}
DATA_HOST_DIR=$(realpath "$DATA_HOST_DIR") || exit 1
RUNS_HOST_DIR=$(realpath "$RUNS_HOST_DIR") || exit 1

# 3. Launch the container interactively
# We mount:
# - the configured host data directory at /app/.data
# - the configured host runs directory at /app/.runs
# - ~/.gemini read-only under /run; entrypoint copies it to ephemeral container storage
# Nested Podman needs mount administration and a wider syscall surface, but not
# Docker's full --privileged bundle. Keep this list explicit and mount no host
# engine socket or host device. Docker's default AppArmor profile denies mount
# operations used by the nested engine, so the outer container must also run
# with an explicit unconfined AppArmor profile on AppArmor-enabled hosts.
if [ ! -d "$ORIG_HOME/.gemini" ]; then
  echo "Error: $ORIG_HOME/.gemini does not exist. Authenticate agy on the host first." >&2
  exit 1
fi

echo "Starting pipeline container in interactive mode (using fish shell)..." >&2
$DOCKER_CMD run -it --init --rm \
  --cap-drop=ALL \
  --cap-add=AUDIT_WRITE \
  --cap-add=CHOWN \
  --cap-add=DAC_OVERRIDE \
  --cap-add=FOWNER \
  --cap-add=FSETID \
  --cap-add=KILL \
  --cap-add=MKNOD \
  --cap-add=NET_BIND_SERVICE \
  --cap-add=NET_RAW \
  --cap-add=SETFCAP \
  --cap-add=SETGID \
  --cap-add=SETPCAP \
  --cap-add=SETUID \
  --cap-add=SYS_ADMIN \
  --cap-add=SYS_CHROOT \
  --cap-add=SYS_RESOURCE \
  --security-opt=apparmor=unconfined \
  --security-opt=seccomp=unconfined \
  --security-opt=no-new-privileges \
  -e PIPELINE_NESTED_PODMAN=1 \
  -e PIPELINE_DATA_DIR=/app/.data \
  -e PIPELINE_RUNS_DIR=/app/.runs \
  -e PIPELINE_SESSION_ROOT="$SESSION_CONTAINER_ROOT" \
  -v "$DATA_HOST_DIR:/app/.data" \
  -v "$RUNS_HOST_DIR:/app/.runs" \
  -v "$ORIG_HOME/.gemini:/run/host-gemini:ro" \
  "$IMAGE_NAME"
