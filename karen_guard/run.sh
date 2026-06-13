#!/bin/bash
# Karen Guard docker runner

# Ensure we are in the script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "Building Karen Guard docker image..."
docker build -t karen_guard .

echo "Starting Karen Guard in interactive mode..."
# Pass current GEMINI_API_KEY and ANTHROPIC_API_KEY from the host shell
docker run -it --rm \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -v "$DIR/../:/app/meta_2028" \
  karen_guard /bin/bash
