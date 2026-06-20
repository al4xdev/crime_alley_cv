# Backlog — Actor-Critic CV Optimization Loop

O core (loop Actor-Critic + Vera/Donna) está estável e os itens planejados originais foram entregues e integrados ao container global.

> Princípio de design (decidido em sessão): migrar pro determinístico **apenas o que
> falha em silêncio**. O que falha alto, o agente cura sozinho — deixa na prosa.

---

## 🚀 Próximos Passos (A Fazer)

### TASK-01: Depuração do Pipeline no Container Global
- Testar e debugar a execução completa do pipeline de otimização dentro do container Docker.
- Rastrear a pasta temporária `/tmp` interna do container e inspecionar os logs de execução em conjunto.
- Validar se o sub-agente `Dependency_Checker` e o `Harvey Shadow` executam com sucesso sob as novas configurações de auto-aprovação de tarefas (`mcp(*)`) e compatibilidade do Podman.

### TASK-02: Otimização de Consumo de Tokens Globais
- **Ignore Global (ex: `.agentignore`)**: Criar um mecanismo de ignore que filtre arquivos desnecessários (como `.lock`, arquivos de configuração de ferramentas, imagens, binários e dependências pesadas) para que **nenhum** agente (não apenas a Karen, mas todos os agentes do pipeline) consuma tokens lendo arquivos irrelevantes durante o processo.
- **Estratégias de Economia Global**: Pesquisar e planejar formas de otimização adicionais, como o uso de *Gemini Context Caching* para dados estáticos compartilhados (como os repositórios clonados e vaga) e telemetria básica para medir o consumo de tokens por iteração.

## ✅ Concluído (Done)

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

---


## Ideias futuras (não priorizadas)

- **Suporte a Múltiplos Provedores de Clientes (agy vs Claude Code)**:
  Expandir a montagem de credenciais no [start.sh](start.sh) e [run.sh](karen_guard/run.sh) para dar suporte à montagem automática de credenciais do Claude Code (ex: `~/.claude/` ou `~/.config/claude/`), permitindo alternar de forma transparente entre o `agy` e outros clientes de agentes.

---

## 🔍 Descobertas da Sessão de Depuração (2026-06-20)

- **Não Persistência de `.dependencies_checked.md` no Docker**:
  Como `/app/` não é montado no host (apenas `.data` e `.runs` são), a verificação de dependências gera o arquivo `.dependencies_checked.md` na raiz do container. Ao parar/reiniciar o container, o arquivo é perdido, forçando a checagem em todo startup.
  *Ideia de Correção*: Salvar em `.data/docs/.dependencies_checked.md` ou expor via volume montado. (Corrigido ✅ - alterado para salvar em `.data/docs/.dependencies_checked.md`)
- **Aviso do Podman no Docker (Storage, Network & Build)**:
  1. *Erro de Storage*: O erro `Failed to obtain podman configuration: runroot must be set` ocorre porque o `storage.conf` gerado no Dockerfile é muito esparso. O sub-agente `Dependency Checker` contornou definindo localmente `CONTAINERS_STORAGE_CONF=/root/.config/containers/storage.conf`. Como o `Harvey Shadow` é isolado, ele teve que redescobrir o erro e aplicar o mesmo contorno.
  2. *Erro de Rede (netavark nftables)*: Ao tentar rodar o build no Podman, o `Harvey Shadow` colidiu com o erro `netavark: nftables error: unable to execute nft` porque o pacote `nftables` não está instalado no Dockerfile. Ele contornou o problema fazendo buscas e preparando um arquivo de override `containers.conf` configurando `firewall_driver="iptables"`.
  3. *Falha de Build com Usuário Root*: Como o container principal roda como `root`, o build-arg padrão tenta criar o usuário `root` (UID 0) no Dockerfile do `karen_guard`, quebrando a instrução `groupadd` (grupo já existe). O sub-agente contornou fixando `--build-arg USERNAME=karen --build-arg USER_ID=1000`.
  *Risco de Ocorrência*: Karen Guard (`run.sh`) vai quebrar se as variáveis `CONTAINERS_STORAGE_CONF` e `CONTAINERS_CONF_OVERRIDE` não estiverem expostas.
  *Ideia de Correção*: No `Dockerfile` principal, (a) instalar o pacote `nftables` ou configurar o firewall driver padrão para `iptables` em `/etc/containers/containers.conf`, (b) ajustar `/etc/containers/storage.conf` com `runroot` e `graphroot` globais, e (c) no `Dockerfile` do `karen_guard`, adicionar verificação para ignorar a criação do usuário se `USERNAME=root`.
- **Segurança de Imagem e Limpeza de Volumes**:
  Identificado e corrigido o vazamento de camadas de imagem adicionando `.data/` e `repos/` ao `.dockerignore`. O volume órfão `karen_guard_alex_home` continha credenciais antigas do host e foi deletado.
- **Entrada de Variáveis em Lote (Batch Input)**:
  O runbook instrui o agente a perguntar as 4 variáveis de setup interativo (`MAX_LOOPS`, `MIN_FIT_SCORE`, etc.) de forma sequencial (uma a uma). No entanto, clientes de agentes modernos como `agy` e `Claude Code` suportam o envio e coleta de múltiplas variáveis de uma só vez (em lote/batch), o que tornaria o setup muito mais ágil.
  *Ideia de Correção*: Otimizar as instruções de setup do runbook para permitir que o agente pergunte/solicite todas as variáveis em uma única interação.
- **Evitar Ciclo de Auto-Cura (Self-Healing) Inútil no Shadow**:
  Como a pasta `.git/` é intencionalmente ignorada no `.dockerignore`, comandos de configuração do git local (como buscar a URL de origem do repositório) **sempre** falharão dentro do container. Atualmente, isso força o `Harvey Shadow` a entrar em um ciclo de auto-cura inútil de tentativas de diagnóstico (o que consome muito tempo e tokens de API) antes de usar o fallback.
  *Ideia de Correção*: Alterar o runbook `shadow.md` para instruir o agente a verificar diretamente se está rodando em container (onde `/app/.git` não existe) e, se sim, ir direto para a extração do usuário a partir do currículo/profile, eliminando as chamadas fracassadas de `git config`.
- **Loop de Autenticação / Travamento no Check do `run.sh`**:
  O script `run.sh` usa `grep -q -E "Error|Authentication|sign in"` sobre a saída de `agy models` para verificar se o CLI está autenticado. Porém, quando o `agy` inicia com sucesso, sua saída de status ou mensagens normais contêm a palavra "signed in" (ex: `You are currently signed in as...`). A busca por `sign in` faz parciais na substring `signed in`, fazendo com que o `run.sh` incorretamente conclua que o CLI **não** está autenticado. Isso dispara a chamada interativa `podman run -it ... karen_guard agy` (fluxo de login), que inicia um terminal interativo headless aguardando input do usuário (o prompt `>`), travando permanentemente a execução em segundo plano.
  *Ideia de Correção*: Realizar uma validação muito mais robusta:
  1. **Usar o Status Code do comando**: A forma mais limpa é simplesmente verificar se `agy models` (ou outro comando rápido) retorna status code `0` (sucesso).
  2. **Usar `agy --print 'oi'`**: O comando não-interativo `agy --print` retorna uma string vazia (ou falha) quando não autenticado, servindo como uma ótima alternativa sem falso positivo textual.




