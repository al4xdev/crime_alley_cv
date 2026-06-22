# Plano de Implementação: Scripts de Fronteira e Contratos entre Agentes

Este plano detalha como as fronteiras entre os agentes do pipeline **Crime Alley CV** serão formalizadas e validadas de forma determinística por meio de ganchos de validação (Assertive Hooks) pré e pós-execução (`boundaries/*.fish`) executados no shell `fish` do host/container. Isso substitui a confiança instrucional (soft constraints) por asserções rígidas e testáveis em código.

---

## 🗺️ Arquitetura de "Assertive Hooks" (Pré e Pós-Condições)

Em vez de os scripts controlarem a execução dos agentes (o que geraria problemas de interatividade e controle de subagentes cognitivos), os scripts de fronteira funcionarão como **Assertive Hooks** síncronos. 

O runbook principal (`harvey_guy/main.md`) invocará as validações antes e depois da execução de cada agente da seguinte forma:
```fish
# Antes de rodar o agente
boundaries/<origem>_<destino>.fish --pre $SESSION_ID

# [Execução do agente coordenada pelo Orquestrador]

# Depois de rodar o agente
boundaries/<origem>_<destino>.fish --post $SESSION_ID
```

Se qualquer validação falhar, o script de fronteira retornará um status code de erro (`exit 1` ou superior), interrompendo o pipeline imediatamente (loud failure).

---

## 🗺️ Detalhamento dos Scripts de Fronteira

Criaremos um diretório `boundaries/` no qual cada transição será encapsulada em um script `.fish`.

### 1. `boundaries/harvey_depchecker.fish` (Fronteira com Dependency Checker)
* **Objetivo**: Garantir que as dependências do host estejam instaladas e válidas.
* **Modo `--pre`**: Nenhuma.
* **Modo `--post`**:
  * Verifica se o arquivo [.data/docs/.dependencies_checked.md](file:///home/alex/git/my/meta_2028/.data/docs/.dependencies_checked.md) existe.
  * Valida se o conteúdo do arquivo é não-vazio e reporta "PASS" para os itens cruciais (`Python`, `uv`, `Docker` ou `Podman`, `at`, `Git`, `wl-copy`).

### 2. `boundaries/harvey_vera.fish` (Fronteira com Vera Onboarding)
* **Objetivo**: Assegurar a integridade do perfil do candidato.
* **Modo `--pre`**: Nenhuma (o orquestrador decide se executa Vera).
* **Modo `--post`**:
  * Valida se [.data/docs/who_are_u.md](file:///home/alex/git/my/meta_2028/.data/docs/who_are_u.md) existe.
  * Valida se possui cabeçalhos obrigatórios markdown (tamanho > 100 bytes) contendo o perfil de experiência estruturado.

### 3. `boundaries/harvey_setup.fish` (Fronteira de Inicialização/Setup)
* **Objetivo**: Validar os insumos do usuário antes da inicialização.
* **Modo `--pre`**:
  * Verifica se [.data/docs/cv.md](file:///home/alex/git/my/meta_2028/.data/docs/cv.md) e [.data/docs/job.md](file:///home/alex/git/my/meta_2028/.data/docs/job.md) existem e são não-vazios.
  * Verifica se a primeira linha de `job.md` corresponde ao formato `# <Cargo> — <Empresa>`.
  * Garante que `MAX_LOOPS` e `MIN_FIT_SCORE` são inteiros válidos.
  * Garante que `KAREN_READS_BACKGROUND` é `"yes"` ou `"no"`.
* **Modo `--post`**:
  * Valida que o diretório `/tmp/karen_guard_$SESSION_ID/` e os subdiretórios `docs/`, `repos/`, `anti_karen/` foram criados.
  * Valida que `docs/cv.md` e `docs/job.md` foram copiados para a sessão.
  * **Roteamento Condicional**:
    * Se `KAREN_READS_BACKGROUND` for `"yes"` e o arquivo `.data/docs/who_are_u.md` existir, garante que ele foi copiado para `SESSION_DIR/docs/who_are_u.md`.
    * Se `KAREN_READS_BACKGROUND` for `"no"` e o arquivo `.data/docs/who_are_u.md` existir, garante que ele foi copiado para `SESSION_DIR/anti_karen/who_are_u.md` (e **não** está presente em `docs/`).

### 4. `boundaries/harvey_shadow.fish` (Fronteira com Harvey Shadow)
* **Objetivo**: Validar a coleta paralela de repositórios e informações.
* **Modo `--pre`**:
  * Garante que `SESSION_DIR` está definido e existe.
* **Modo `--post`**:
  * Garante que `SESSION_DIR/company_info.md` existe e é não-vazio.
  * Lê o arquivo de contagem esperada (ex: `SESSION_DIR/repos_expected_count.txt` ou similar se gerado, ou valida se a pasta `repos/` foi criada). Se repositórios eram esperados, garante que foram baixados.

### 5. `boundaries/harvey_karen.fish` (Fronteira com Karen Guard)
* **Objetivo**: Rodar a auditoria na sandbox de forma isolada e autenticada.
* **Modo `--pre`**:
  * Verifica se `SESSION_DIR/docs/cv.md` e `SESSION_DIR/docs/job.md` existem.
  * **Verificação de Liveness Autenticada**: Roda um comando rápido de teste do `agy` no host (ex: `agy models`) para garantir que o token oauth local não está corrompido ou expirado.
* **Modo `--post`**:
  * Garante que `SESSION_DIR/anti_karen/evaluation.md` foi gerado e é não-vazio.
  * **Validação Física**: Garante que nenhum arquivo fora de `out/` (no mount de escrita) foi modificado no container Karen.

### 6. `boundaries/karen_gatekeeper.fish` (Fronteira com o Gatekeeper)
* **Objetivo**: Avaliar os critérios de saída do loop determinístico.
* **Modo `--pre`**:
  * Garante que `SESSION_DIR/anti_karen/evaluation.md` existe.
* **Modo `--post`**:
  * Captura o código de retorno do gatekeeper.
  * Se o status for `0` (sucesso) ou `1` (max_loops), valida que o currículo final da iteração foi copiado de volta para o host em [.data/docs/cv.md](file:///home/alex/git/my/meta_2028/.data/docs/cv.md).

### 7. `boundaries/gatekeeper_bill.fish` (Fronteira com Bill Editor)
* **Objetivo**: Prevenir fraudes de contexto, alucinações de arquivos e modificações fora da sessão.
* **Modo `--pre`**:
  * Garante que `SESSION_DIR/docs/cv.md` existe.
  * **Segurança contra Fraude de Contexto**: Salva os hashes SHA-256 iniciais das fontes de verdade da sessão: `docs/job.md`, `anti_karen/who_are_u.md` (se existir), `docs/who_are_u.md` (se existir) e `company_info.md`.
  * Cria uma lista de snapshots de arquivos modificados no repositório host (usando `git diff --name-only`).
* **Modo `--post`**:
  * Garante que `SESSION_DIR/docs/cv.md` foi modificado pelo Bill (tamanho ou hash diferem do inicial).
  * **Verificação contra Modificações Indevidas**: Garante que o Bill não alterou nenhum arquivo rastreado pelo git no repositório principal (comparando com o snapshot inicial).
  * **Verificação Anti-Fraude**: Recalcula e compara os hashes SHA-256 de `job.md`, `who_are_u.md` e `company_info.md` para garantir que o Bill não os alterou para burlar o fit score da Karen.

### 8. `boundaries/bill_harvey.fish` (Fronteira de Carry Forward)
* **Objetivo**: Conduzir o currículo otimizado com segurança para a próxima iteração.
* **Modo `--pre`**:
  * Garante que `SESSION_DIR/docs/cv.md` difere de `.data/docs/cv.md`.
* **Modo `--post`**:
  * Copia o currículo modificado para o host [.data/docs/cv.md](file:///home/alex/git/my/meta_2028/.data/docs/cv.md).
  * Incrementa `CURRENT_LOOP`.
  * Escreve o estado no checkpoint `/tmp/karen_guard_loop_state.json`.

### 9. `boundaries/gatekeeper_donna.fish` (Fronteira com Donna Career Coach)
* **Objetivo**: Garantir a geração correta do plano de desenvolvimento final.
* **Modo `--pre`**:
  * Garante que o relatório de avaliação final em `SESSION_DIR/anti_karen/evaluation.md` existe.
* **Modo `--post`**:
  * Valida que [.data/docs/action_plan.md](file:///home/alex/git/my/meta_2028/.data/docs/action_plan.md) foi gerado e não está vazio.

---

## 🧪 Estratégia de Testes Unitários (`tests/test_boundaries.py`)

Escreveremos a suíte de testes unitários `tests/test_boundaries.py` em Python (pytest) que irá:
1. **Mockar cenários de sucesso e falha**: Criará diretórios de sessão temporários, com arquivos válidos, inválidos ou ausentes.
2. **Invocar os scripts de fronteira**: Roda os scripts fish de fronteira via `subprocess` e garante que retornam `exit code 0` nas pré/pós condições corretas e `exit code != 0` em caso de quebra de contrato.
3. **Testar integridade SHA-256**: Fornece um cenário onde simulamos o Bill editando `job.md` de forma maliciosa e verifica se `gatekeeper_bill.fish --post` pega a fraude e aborta com erro.

---

## 📅 Plano de Ação para Implementação

1. **Escrever os Scripts de Fronteira**: Criar o diretório `boundaries/` e escrever os arquivos `.fish` aplicando os padrões de hooks pré/pós e asserções.
2. **Escrever e Rodar a Suite de Testes**: Implementar `tests/test_boundaries.py` e executar `uv run pytest tests/test_boundaries.py` até que todos os casos de teste passem.
3. **Corrigir Erros no Runbook Principal**:
   * Ajustar o link incorreto da Donna para apontar para `../donna_nana/main.md`.
   * Ajustar a lógica do checkpoint no Step 1 para não resetar o `session_id` se `CURRENT_LOOP > 0`.
4. **Integrar os Hooks no Runbook**: Modificar `harvey_guy/main.md` inserindo chamadas explícitas aos scripts `--pre` e `--post` em cada transição relevante de agente.
