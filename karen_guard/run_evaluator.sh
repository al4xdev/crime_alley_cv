#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Self-healing: if current shell lacks docker socket permissions, retry with sg docker
if ! docker ps >/dev/null 2>&1; then
  echo "No permission to access Docker socket. Retrying command via 'sg docker'..."
  exec sg docker -c "$0 $*"
fi

if [ -z "$1" ]; then
  echo "Usage: ./run.sh <session_id>"
  exit 1
fi

SESSION_ID="$1"
SESSION_DIR="/tmp/karen_guard_${SESSION_ID}"

if [ ! -d "$SESSION_DIR" ]; then
  echo "Error: Session directory $SESSION_DIR does not exist."
  exit 1
fi

HOST_USER=$(whoami)
HOST_UID=$(id -u)

echo "Building base Karen Guard docker image..."
docker build -t karen_guard \
  --build-arg USERNAME="${HOST_USER}" \
  --build-arg USER_ID="${HOST_UID}" .

echo "Checking Antigravity CLI authentication..."

# O SEU TESTE: Pede pra IA falar "teste". Se não sair "teste" (ou retornar vazio), precisa logar.
if ! docker run --rm karen_guard su - "${HOST_USER}" -c "agy --print 'teste'" 2>/dev/null | grep -qi "teste"; then
    echo "Antigravity CLI is not authenticated (or failed to respond). Starting interactive login flow..."
    
    # Remove qualquer container de auth preso de tentativas anteriores
    docker rm -f karen_guard_auth 2>/dev/null

    # 1. Roda o container SEM a flag --rm (para ele não se autodestruir ao sair)
    docker run -it --name karen_guard_auth karen_guard su - "${HOST_USER}" -c "agy"
    
    # 2. Assim que você sair do AGY, o script retoma e FAZ O COMMIT AUTOMÁTICO!
    echo "Saving authentication state directly into the Docker image..."
    docker commit karen_guard_auth karen_guard:latest
    docker rm karen_guard_auth
    echo "Auth baked into karen_guard:latest successfully!"
fi

# ---------------------------------------------------------
# SETUP HEADLESS (Sem pedir permissão 'y/n')
# ---------------------------------------------------------
# Criamos o arquivo config.json isolado na pasta temporária
CONFIG_FILE="${SESSION_DIR}/config.json"
cat << 'EOF' > "$CONFIG_FILE"
{
  "userSettings": {
    "globalPermissionGrants": {
      "allow": [
        "unsandboxed(bash)",
        "unsandboxed(sh)",
        "command(*)",
        "read_file(*)",
        "write_file(*)",
        "read_url(*)"
      ],
      "deny": [
        "command(rm)",
        "command(rm -rf)",
        "write_file(/etc)"
      ]
    },
    "useAiCredits": false
  }
}
EOF
chown "${HOST_UID}:${HOST_UID}" "$CONFIG_FILE"

echo "Starting Karen Guard evaluation process for session ${SESSION_ID}..."

# Roda o container avaliador.
docker run -it --rm \
  -v "${SESSION_DIR}:/app/session" \
  -v "${CONFIG_FILE}:/home/${HOST_USER}/.gemini/config/config.json" \
  karen_guard su - "${HOST_USER}" -c "run_evaluator"