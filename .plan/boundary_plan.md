# Plano de Implementação: Scripts de Fronteira e Contratos entre Agentes

Este plano detalha como as fronteiras entre os agentes do pipeline **Crime Alley CV** serão formalizadas e validadas de forma determinística por meio de scripts de fronteira (`boundaries/*.fish`) executados no shell `fish` do host/container. Isso substitui a confiança instrucional (soft constraints) por asserções rígidas e testáveis em código.

---

## 🗺️ Mapa de Transições e Contratos de Fronteira

Criaremos um diretório `boundaries/` no qual cada transição de agente será encapsulada em um script `boundaries/<origem>_<destino>.fish` (ou nome similar indicando a transição). Cada script terá três fases claras:
1. **Pré-condições**: Validação determinística de variáveis de ambiente, arquivos de entrada obrigatórios e esquemas básicos de dados.
2. **Execução**: Chamada da ação real (execução do script Python, container ou sinalização para o usuário/agente interagir).
3. **Pós-condições**: Verificação de que as saídas esperadas foram geradas com sucesso, estão no local correto, não violam permissões e não introduziram modificações indevidas no host.

Abaixo está o mapeamento detalhado das transições planejadas:

### 1. `boundaries/harvey_depchecker.fish` (Fronteira com Dependency Checker)
* **Objetivo**: Garantir que as dependências do host estejam instaladas e válidas.
* **Pré-condição**: Nenhuma (script executa a checagem do zero se forçar re-run, ou pula se o marker existir).
* **Ação**: Executa as verificações descritas em `requirements.md` (ou delega para o subagente).
* **Pós-condição**: Verifica se o arquivo [.data/docs/.dependencies_checked.md](file:///home/alex/git/my/meta_2028/.data/docs/.dependencies_checked.md) existe, é não-vazio e reporta "PASS" para todos os itens.

### 2. `boundaries/harvey_vera.fish` (Fronteira com Vera Onboarding)
* **Objetivo**: Assegurar a existência e o formato básico do histórico/background do candidato.
* **Pré-condição**: Se [.data/docs/who_are_u.md](file:///home/alex/git/my/meta_2028/.data/docs/who_are_u.md) existir, pede confirmação para reuse/refresh.
* **Ação**: Executa Vera para criar/atualizar o arquivo.
* **Pós-condição**: Valida se [.data/docs/who_are_u.md](file:///home/alex/git/my/meta_2028/.data/docs/who_are_u.md) existe, tem tamanho > 100 bytes e possui cabeçalhos obrigatórios markdown (ex: contendo informações estruturadas de experiência).

### 3. `boundaries/harvey_setup.fish` (Fronteira de Inicialização/Setup)
* **Objetivo**: Validar os insumos iniciais fornecidos pelo usuário e inicializar a sessão do Harvey.
* **Pré-condição**:
  * Presença e integridade de [.data/docs/cv.md](file:///home/alex/git/my/meta_2028/.data/docs/cv.md) e [.data/docs/job.md](file:///home/alex/git/my/meta_2028/.data/docs/job.md).
  * O arquivo `job.md` deve conter um título de vaga válido na primeira linha (formato `# <Cargo> — <Empresa>`).
  * As variáveis `MAX_LOOPS` e `MIN_FIT_SCORE` devem ser inteiros válidos.
  * `KAREN_READS_BACKGROUND` deve ser `"yes"` ou `"no"`.
* **Ação**: Executa `uv run python harvey_guy/main.py` para criar a sessão e obter o `SESSION_ID`.
* **Pós-condição**:
  * O diretório `/tmp/karen_guard_$SESSION_ID/` foi criado.
  * O layout isolado foi estruturado (`docs/`, `repos/`, `anti_karen/`).
  * O arquivo `who_are_u.md` foi copiado para a pasta correta (dentro de `docs/` se `yes`, dentro de `anti_karen/` se `no`).

### 4. `boundaries/harvey_shadow.fish` (Fronteira com Harvey Shadow)
* **Objetivo**: Validar a ingestão paralela de informações da empresa e dos repositórios do candidato.
* **Pré-condição**:
  * A variável `SESSION_DIR` (/tmp/karen_guard_$SESSION_ID) deve estar definida e activa.
* **Ação**: Executa as tarefas do Harvey Shadow (pesquisa e clonagem de repositórios).
* **Pós-condição**:
  * O arquivo `SESSION_DIR/company_info.md` existe e não é vazio.
  * O diretório `SESSION_DIR/repos/` existe e possui ao menos um subdiretório ou arquivo clonado (se houver repositórios informados no perfil do candidato).

### 5. `boundaries/harvey_karen.fish` (Fronteira com Karen Guard)
* **Objetivo**: Executar a auditoria na sandbox com segurança de volume e chaves.
* **Pré-condição**:
  * `SESSION_DIR` e subdiretórios `docs/`, `repos/` e arquivo `company_info.md` presentes.
  * Presença de credenciais válidas do agy no host (`~/.gemini/antigravity-cli/antigravity-oauth-token`).
* **Ação**: Executa `./karen_guard/run.sh $SESSION_ID` com logs isolados.
* **Pós-condição**:
  * Geração do arquivo `SESSION_DIR/anti_karen/evaluation.md`.
  * Validação física: o container Karen não deve ter escrito fora do diretório `out/` (que é mapeado no container).

### 6. `boundaries/karen_gatekeeper.fish` (Fronteira com o Gatekeeper)
* **Objetivo**: Avaliar o encerramento ou prosseguimento do loop determinístico.
* **Pré-condição**:
  * Presença de `SESSION_DIR/anti_karen/evaluation.md`.
* **Ação**: Executa `uv run python harvey_guy/gatekeeper.py ...` extraindo o score de forma tolerante.
* **Pós-condição**:
  * Saída de status válida (0: Sucesso, 1: Limite de loops, 2: Continua loop).
  * Se status for 0 ou 1, garante que a versão final do currículo foi copiada com segurança de volta para o host em [.data/docs/cv.md](file:///home/alex/git/my/meta_2028/.data/docs/cv.md).

### 7. `boundaries/gatekeeper_bill.fish` (Fronteira com Bill Editor)
* **Objetivo**: Garantir que as edições de CV do Bill respeitem restrições e não adulterem outros arquivos.
* **Pré-condição**:
  * Presença de `SESSION_DIR/docs/cv.md` original, relatório de auditoria `karen_output.md` e ground-truth `who_are_u.md`.
* **Ação**: Spawna o agente Bill.
* **Pós-condição**:
  * O arquivo `SESSION_DIR/docs/cv.md` foi modificado (conteúdo é diferente do inicial).
  * **Verificação Anti-Trust/Anti-Hallucination**: NENHUM arquivo no repositório host (rastreado pelo git) foi modificado pelo Bill. Validação feita comparando `git diff --name-only` do repositório host e verificando timestamps.

### 8. `boundaries/bill_harvey.fish` (Fronteira de Carry Forward)
* **Objetivo**: Conduzir o currículo revisado pelo Bill para a próxima iteração com segurança.
* **Pré-condição**:
  * O currículo atualizado em `SESSION_DIR/docs/cv.md` é válido e difere do anterior.
* **Ação**:
  * Copia o currículo modificado para o host [.data/docs/cv.md](file:///home/alex/git/my/meta_2028/.data/docs/cv.md).
  * Incrementa `CURRENT_LOOP` e escreve o checkpoint atualizado em `/tmp/karen_guard_loop_state.json`.
* **Pós-condição**:
  * O checkpoint `/tmp/karen_guard_loop_state.json` existe e reflete o incremento correto de loops.

### 9. `boundaries/gatekeeper_donna.fish` (Fronteira com Donna Career Coach)
* **Objetivo**: Gerar o plano de desenvolvimento pós-loop.
* **Pré-condição**:
  * Presença de `SESSION_DIR/anti_karen/evaluation.md`.
* **Ação**: Spawna a agente Donna.
* **Pós-condição**:
  * O arquivo [.data/docs/action_plan.md](file:///home/alex/git/my/meta_2028/.data/docs/action_plan.md) foi criado e contém seções estruturadas sobre gaps técnicos e plano de ação.

---

## 🧪 Estratégia de Testes Unitários (`tests/test_boundaries.py`)

Para comprovar que esses scripts impedem falhas silenciosas e alucinações de caminhos de arquivos, escreveremos testes unitários usando `pytest`. 
Os testes irão:
1. **Mockar estados do filesystem** (pastas temporárias criadas pelo pytest `tmp_path`).
2. **Executar os scripts de fronteira** (`boundaries/*.fish`) usando `subprocess` passando caminhos mockados.
3. **Validar falha controlada**: Garantir que se uma pré-condição ou pós-condição falhar (ex: faltar `cv.md` ou se Bill modificar um arquivo proibido), o script retorne um status code de erro (`!= 0`).

---

## 📅 Plano de Execução do Agente

1. **Submissão do Plano para Validação por Subagente**:
   * Invocar o subagente `research` para avaliar este plano de implementação e dar feedback sobre consistência, edge cases e conformidade com o projeto.
2. **Refinamento**:
   * Ajustar o plano com base nas correções do subagente.
3. **Criação dos Scripts**:
   * Escrever os scripts `.fish` na pasta `boundaries/`.
4. **Implementação dos Testes**:
   * Escrever a suite de testes unitários em `tests/test_boundaries.py`.
   * Garantir que todas as asserções rodem localmente e passem via `pytest`.
5. **Integração no Fluxo de Orquestração**:
   * Atualizar [harvey_guy/main.md](file:///home/alex/git/my/meta_2028/harvey_guy/main.md) para chamar esses scripts de fronteira em cada transição, ao invés de usar comandos ad-hoc de movimentação direta ou confiar em subagentes.
