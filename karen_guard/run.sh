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

echo "Building Karen Guard docker image for user ${HOST_USER} (UID ${HOST_UID})..."
docker build -t karen_guard \
  --build-arg USERNAME="${HOST_USER}" \
  --build-arg USER_ID="${HOST_UID}" .

# ---------------------------------------------------------
# SETUP DO AMBIENTE ISOLADO DA IA (.gemini)
# ---------------------------------------------------------
SESSION_GEMINI_DIR="${SESSION_DIR}/.gemini"
mkdir -p "${SESSION_GEMINI_DIR}/config"

echo "Preparing isolated Antigravity CLI environment..."
# 1. Copia as credenciais do host (se existirem)
if [ -d "${HOME}/.gemini" ]; then
    cp -R "${HOME}/.gemini/." "${SESSION_GEMINI_DIR}/" 2>/dev/null || true
    # Remove a pasta 'brain' para isolar totalmente o histórico e os prompts do host
    rm -rf "${SESSION_GEMINI_DIR}/brain"
fi

# 2. Injeta o config.json hardcoded para o agente rodar os comandos sem pedir permissão (headless)
cat << 'EOF' > "${SESSION_GEMINI_DIR}/config/config.json"
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

# Ajusta as permissões da pasta temporária para o usuário do host
chown -R "${HOST_UID}:${HOST_UID}" "${SESSION_GEMINI_DIR}"
# ---------------------------------------------------------

echo "Checking Antigravity CLI authentication..."
# Teste de autenticação apontando para a pasta isolada mapeada como /home/user/.gemini
if docker run --rm -v "${SESSION_GEMINI_DIR}:/home/${HOST_USER}/.gemini" \
    karen_guard su - "${HOST_USER}" -c "agy models" 2>&1 | grep -q -E "Error|Authentication|sign in"; then
    
    echo "Antigravity CLI is not authenticated. Starting interactive login flow..."
    # Login interativo. A credencial gerada ficará salva na pasta SESSION_GEMINI_DIR
    docker run -it --rm \
      -v "${SESSION_GEMINI_DIR}:/home/${HOST_USER}/.gemini" \
      karen_guard su - "${HOST_USER}" -c "agy"
      
    echo "Login efetuado! Retomando execução do avaliador..."
    
    # Se fez o login, opcionalmente sincronizamos a credencial de volta para o host para uso futuro
    cp -R "${SESSION_GEMINI_DIR}/"* "${HOME}/.gemini/" 2>/dev/null || true
fi

echo "Starting Karen Guard evaluation process for session ${SESSION_ID}..."
# Roda a IA com a sessão de arquivos e o contexto .gemini isolado e com bypass de prompts
docker run -it --rm \
  -v "${SESSION_DIR}:/app/session" \
  -v "${SESSION_GEMINI_DIR}:/home/${HOST_USER}/.gemini" \
  karen_guard su - "${HOST_USER}" -c "run_evaluator"