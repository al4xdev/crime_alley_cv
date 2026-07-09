# Refatoração das Fronteiras e Monitoramento (Watchdog)

Este diretório contém o plano e documentações de suporte para a execução refinada das fronteiras entre os agentes cognitivos do projeto.

---

## 🎯 Resumo da Refatoração Realizada

A refatoração implementou contratos determinísticos baseados em **Pydantic (modo estrito)** e renderização de templates **Jinja2** para os três agentes cognitivos do fluxo:
1. **Harvey Shadow** (coleta de contexto e preparação do ambiente).
2. **Bill** (reconstrução e otimização do currículo).
3. **Donna** (geração do plano de ação de carreira pós-loop).

### 🛠️ O que foi resolvido e refinado:
* **Prevenção de Problemas de Aspas (Fish Shell):** Substituímos o envio de payloads JSON como strings CLI (`--data`) pela gravação de arquivos temporários (`--data-file <path>`), usando `jq -n` para serialização segura e sem erros de escape de aspas no Fish.
* **Isolamento de Testes Unitários:** Adicionamos suporte à variável `BOUNDARY_REPO_ROOT` em todos os ganchos Fish para garantir que os caminhos dinâmicos das suítes de teste (resolvidos via `status dirname`) apontem para os diretórios mockados do pytest.
* **Resolução de Ambiguidade de Nomes:** Padronizamos o arquivo de saída da avaliação de Karen Guard para `karen_output.md` em toda a cadeia.
* **Segurança e Coesão:** Mantivemos os agentes utilitários e operacionais (como Setup, Vera e Gatekeeper) fora do escopo do Pydantic para evitar overhead desnecessário, mantendo validações simples e focadas.

---

## 🐶 Como Executar o Diagnóstico / Watchdog

Para monitorar a execução da pipeline em tempo real (mesmo se ela estiver rodando isolada dentro de um container Docker/Podman), criamos um script utilitário de diagnóstico inteligente.

Ele está salvo nos rascunhos persistentes da sessão em:
`/home/alex/.gemini/antigravity-cli/brain/eab3cedf-da88-471d-bce4-61abf89b8c5b/scratch/watchdog.fish`

### ⚙️ Como o Watchdog Funciona:
1. **Detecção do Docker:** Ele verifica automaticamente se existe um container rodando a imagem `crime_alley_pipeline` no host.
2. **Introspecção Intracontainer:** Se o container estiver ativo, ele executa comandos `docker exec` de forma segura para ler o `/tmp` de dentro da sandbox, tailando os logs (`karen_guard_core.log`, `karen_run.log`) e checando a lista de processos internos (como builds do Podman em progresso).
3. **Fallback para o Host:** Se o container não estiver rodando, ele monitora a persistência local nos volumes montados do host (`.data/docs/` e `.runs/`).

### 🚀 Como Rodar o Watchdog no Host:
Basta executar o comando abaixo a partir do seu terminal no host:
```bash
fish /home/alex/.gemini/antigravity-cli/brain/eab3cedf-da88-471d-bce4-61abf89b8c5b/scratch/watchdog.fish
```
