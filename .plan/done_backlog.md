# Completed Backlog History — Crime Alley CV

This file stores the completed tasks history to keep the main `.plan/backlog.md` clean and lightweight.

## ✅ Concluído (Done)

### TASK-01: Depuração do Pipeline no Container Global
- **Problema**: Testar o fluxo completo de dependências, Shadow e Karen Guard dentro do container global.
- **Resolução**: Validamos com sucesso o setup de dependências (resolvida a instalação de pacotes e ativação de serviços), corrigimos o mount de diretórios e o problema de autenticação automática da Karen.
- **Descoberta do DNS do Podman**: Identificamos e corrigimos o erro de DNS do Podman aninhado passando `--dns=8.8.8.8` no script `run.sh`, eliminando o loop infinito de login interativo.

### 📝 Plano de Retorno (Pós-Almoço)
- [x] **Re-ativar o watchdog**: Criada e posteriormente cancelada a tarefa de monitoramento.
- [x] **Disparar a Execução**: Executado com sucesso o orquestrador no container.
- [x] **Efetuar Login do `agy`**: Autenticação bypassada com sucesso após o fix do DNS.
- [x] **Acompanhar Logs & Checkpoints**: Logs validados no host e container.

### TASK-03: Correção de Rede e Storage do Podman no Dockerfile
- **Arquivo**: `Dockerfile` principal do projeto
- **Problema**: O Podman rodando dentro do container Docker principal falha no build/run sem firewall driver (`nftables` ou `iptables`) e sem as configurações de `runroot` em `/etc/containers/storage.conf`.
- **Solução**: 
  1. Instalar o pacote `nftables` via `apt-get` no `Dockerfile` principal.
  2. Adicionar o arquivo `/etc/containers/containers.conf` configurando `firewall_driver = "iptables"`.
  3. Estruturar `/etc/containers/storage.conf` para pré-definir as pastas de root/storage corretas de modo global no container.
- **Validação**: Executar `podman info` dentro do container principal como root e verificar se reporta a configuração de rede e storage sem warnings ou erros de `runroot`.
- **Critérios de Aceitação**:
  - `podman info` no container principal não exibe mensagens de erro de storage ou rede.
  - É possível realizar build e run no Podman dentro do Docker sem exportar manualmente `CONTAINERS_STORAGE_CONF` localmente nos subagentes.

### TASK-04: Resolução de Usuário Root e GID 0 no Dockerfile do Karen Guard
- **Arquivos**: `karen_guard/Dockerfile` e `karen_guard/run.sh`
- **Problema**: Quando o host roda como root (UID 0), o script repassa `USERNAME=root` e `USER_ID=0` nos build-args, quebrando a instrução `groupadd` no Dockerfile (pois o grupo root já existe).
- **Solução**:
  1. No `karen_guard/Dockerfile`, ajustar o bloco de criação de usuário para verificar se o UID/GID solicitado já existe ou se o `USERNAME` é `root`. Se sim, pular a criação do grupo/usuário.
  2. Alternativamente, no `karen_guard/run.sh`, se `HOST_UID` for 0, mapear o build-arg para um usuário alternativo (ex: `karen` com UID 1000) e tratar as permissões correspondentes.
- **Validação**: Rodar `./karen_guard/run.sh` com usuário root no host e verificar se a imagem `karen_guard` é compilada sem erros de `groupadd` / exit code 9.
- **Critérios de Aceitação**:
  - Compilação do Dockerfile do `karen_guard` em ambientes root e não-root sem falhas de criação de usuário/grupo.

### TASK-05: Validação Robusta de Autenticação do agy em run.sh
- **Arquivo**: `karen_guard/run.sh` (linhas ~97-120)
- **Problema**: O comando `grep -q -E "Error|Authentication|sign in"` sobre a saída de `agy models` gera falso positivo pois um login bem-sucedido retorna mensagens contendo "signed in", travando o container headless em loop de login interativo.
- **Mocks & Testes Criados**:
  - Os arquivos de mock gerados nesta sessão (`company_info.md`, `repos.json`, `repos_expected_count.txt` e `anti_karen/who_are_u.md`) foram copiados para a pasta [tests/mocks/](file:///home/alex/git/my/meta_2028/tests/mocks/) para servir como fixtures.
  - A suíte de testes unitários [tests/test_run_sh.py](file:///home/alex/git/my/meta_2028/tests/test_run_sh.py) foi implementada para testar o comportamento do script utilizando mocks de execução.
  - *Instrução para o Próximo Agente*: Use e revise estes mocks e testes para validar a integridade de todas as suas alterações no ambiente de script sem precisar interagir com os LLMs dos agentes diretamente (otimizando tempo e cota de tokens).
- **Solução**:
  1. Substituir o check textual por uma checagem direta do exit code do comando: `podman run ... exam_guard agy models >/dev/null 2>&1` e checar `$status` / `$?`.
  2. Alternativamente, usar `agy --print 'oi'` (ou `agy -p 'oi'`) e verificar se a saída não é vazia.
- **Critérios de Aceitação**:
  - Modificar o check em `run.sh` para usar o status code ou `--print 'oi'`.
  - Inverter a asserção no teste `test_run_sh_auth_false_positive_reproduces_bug` em [tests/test_run_sh.py](file:///home/alex/git/my/meta_2028/tests/test_run_sh.py) para que ele passe apenas quando o fluxo interativo **não** for disparado por falso positivo.
  - O agente deve revisar a suíte de testes criada. Todos os testes unitários em `tests/test_run_sh.py` devem passar (`pytest tests/test_run_sh.py`) como critério de aceitação de entrega da tarefa.

### TASK-06: Otimização de Entrada de Variáveis (Batch Input)
- **Arquivo**: `harvey_guy/harvey_guy.py` (ou nos runbooks de setup)
- **Problema**: O setup interativo do runbook pede que o agente pergunte as 4 variáveis de controle (`MAX_LOOPS`, `MIN_FIT_SCORE`, etc.) individualmente, gerando múltiplas iterações caras e lentas.
- **Solução**: Alterar as instruções de coleta de variáveis para solicitar explicitamente que o agente peça e extraia todas as variáveis de uma única vez em lote (batch request).
- **Critérios de Aceitação**:
  - O prompt de setup solicita todas as 4 configurações em uma única chamada.

### TASK-07: Eliminação de Auto-Cura Inútil de Git no Harvey Shadow
- **Arquivo**: Runbook do Harvey Shadow (`harvey_guy/shadow.md` ou similar)
- **Problema**: Com `.git` ignorado no `.dockerignore`, comandos locais de git config/remote falham e o subagente entra em ciclos longos de auto-cura desnecessários.
- **Solução**: Instruir o subagente a verificar diretamente a existência da pasta `/app/.git` e, caso não exista (indicação de ambiente de container), pular diretamente para a estratégia de fallback (ingestão pelo currículo/profile).
- **Critérios de Aceitação**:
  - O subagente não executa `git config` nem `git remote` se `/app/.git` estiver ausente, indo direto para a carga do profile de onboarding.

### TASK-08: Remoção de Dependência de Wayland & Ativação do atd no Docker
- **Problema**: Remover os requisitos de Wayland e configurar inicialização automática do `atd` no container.
- **Resolução**: Removemos todas as menções e requisitos do Wayland (`wl-copy`/`wl-clipboard`) do pipeline e documentos. Criamos o `entrypoint.sh` e atualizamos o `Dockerfile` para iniciar o daemon `/usr/sbin/atd` automaticamente no container.

### TASK-09: Correção de Pulo de Perguntas pós-retorno do Pager agy
- **Problema**: Terminal stdin corrompido ao suspender ou retornar de subprocessos interativos/pagers como o do `agy`.
- **Resolução**: Substituímos a delegação para o subagente `Dependency Checker` por uma execução direta no fluxo do orquestrador principal, evitando a corrupção do terminal e permitindo a coleta de inputs iterativos com segurança.

### TASK-10: Restrições de Prompt e Rede da Karen Guard
- **Problema**: A Karen tentava acessar a internet/clonar repositórios e fazia buscas globais no filesystem root (`/`), causando lentidão e timeouts.
- **Resolução**: Ajustamos a persona em `karen_guard/prompt_persona.txt` impondo restrições rígidas: sem acesso à internet, buscas de arquivos limitadas estritamente aos repositórios pré-clonados localizados em `/app/session/repos/`.

---

## 🔍 Novas Descobertas Históricas
- **Sobrescrita do Token de Autenticação do Host por Testes Unitários (Corrigido ✅)**: O script `karen_guard/run.sh` resolvia o diretório home do usuário utilizando `getent passwd "$HOST_USER" | cut -d: -f6`, que retornava `/home/alex` mesmo sob o mock de testes unitários. Isso fazia com que a cópia final pós-login do mock de teste sobrescrevesse o token real do usuário no host em `/home/alex/.gemini/antigravity-cli/antigravity-oauth-token` com `"mock-oauth-token"`. Ajustado `run.sh` para priorizar a variável de ambiente `$HOME`.
