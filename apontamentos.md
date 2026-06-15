# Apontamentos — Actor-Critic CV Optimization Loop

Registro de todos os problemas identificados e corrigidos durante a revisão do projeto (sessão 2026-06-15).

---

## Bugs Críticos (Corrigidos)

### 1. `docker run -it` com output redirecionado — `karen_guard/run.sh`
**Problema**: O run principal do Karen usava `docker run -it`, mas em `harvey_guy/main.md` o comando é chamado com stdout/stderr redirecionados para arquivo. Docker falha com "the input device is not a TTY" nesse cenário.
**Correção**: Removido o flag `-t` (mantido sem flags de TTY no run principal).

### 2. Falha silenciosa quando `evaluation.md` não é gerado — `karen_guard/run.sh`
**Problema**: O bloco `if [ -f evaluation.md ]` era silencioso quando o arquivo não existia — nenhum erro emitido, stdout vazio, pipeline quebrava sem diagnóstico.
**Correção**: Adicionado `else` com mensagem de erro para stderr e `exit 1`.

### 3. `KAREN_REPORT_PATH` com path incorreto — `billf/main.md`
**Problema**: O exemplo mostrava `/tmp/karen_guard_$SESSION_ID/karen_output.md`, mas o arquivo real está em `/tmp/karen_guard_$SESSION_ID/anti_karen/karen_output.md`. Bill tentaria ler o caminho errado.
**Correção**: Corrigido o path de exemplo para incluir `/anti_karen/`.

### 4. Formato do `FIT_SCORE` ambíguo — `karen_guard/prompt_persona.txt`
**Problema**: A instrução de score ficava dentro de um bullet sob `## 1. Overview and Job Fit`, pedindo um `##` heading dentro de um `-` bullet — instrução estruturalmente confusa para o modelo Gemini.
**Correção**: Score movido para seção `##` própria no topo do relatório, com instrução de formato explícita e nota de que é parseado programaticamente.

---

## Bugs Moderados (Corrigidos)

### 5. `$*` sem aspas no re-exec `sg docker` — `karen_guard/run.sh`
**Problema**: `exec sg docker -c "$0 $*"` não preserva quoting de argumentos. Improvável com UUID mas tecnicamente incorreto.
**Correção**: Substituído por `$(printf '%q ' "$@")`.

### 6. Sem `exit 1` após falha do `docker build` — `karen_guard/run.sh`
**Problema**: Se o build falhasse, o script continuava e o `docker run` posterior falhava com erro não relacionado, sem diagnóstico claro.
**Correção**: Adicionado `|| { echo "Error: Docker build failed." >&2; exit 1; }`.

### 7. `chown HOST_UID:HOST_UID` — `karen_guard/run.sh`
**Problema**: Usava UID como GID, funcionava apenas porque o Dockerfile força GID == UID. Frágil em outros contextos.
**Correção**: Adicionado `HOST_GID=$(id -g)` e corrigido para `HOST_UID:HOST_GID`.

### 8. Docker image reconstruída em toda iteração do loop — `karen_guard/run.sh`
**Problema**: Harvey Shadow pré-builda a imagem, mas `run.sh` rebuilda incondicionalmente a cada chamada.
**Correção**: Adicionado `docker image inspect karen_guard` para skip se imagem já existe.

### 9. `ingest_documents()` silenciosa se `data/docs/` vazio — `harvey_guy/harvey_guy.py`
**Problema**: Se `cv.md` ou `job.md` não existissem, o loop iterava sem fazer nada. O pipeline só falharia tarde, em Karen, sem contexto claro.
**Correção**: Adicionada validação explícita com `FileNotFoundError` antes do loop.

### 10. Verificação duplicada do `at` utility — `harvey_guy/main.md` (ex-`core.md`)
**Problema**: Phase 1 pedia ao orchestrator para verificar o `at` utility interativamente — exatamente o que o Dependency Checker já faz na Phase 0.
**Correção**: Removido do Phase 1.

---

## Problemas de Estilo Python (Corrigidos)

### 11. `__init__` com lógica em runtime — `harvey_guy/harvey_guy.py`
**Problema**: `__init__` executava `getpass.getuser()`, `os.getuid()` e fazia assignments diretos — viola `style.md` regra #2 (constructor reservado para TYPE_CHECKING).
**Correção**: Toda lógica removida do `__init__`, que agora contém apenas o bloco `TYPE_CHECKING`.

### 12. Dead code: `host_user`, `host_uid`, `github_username`, `documentation_dir` — `harvey_guy/harvey_guy.py`
**Problema**: Atributos definidos mas nunca usados no código Python (responsabilidade migrada para Harvey Shadow e `run.sh`).
**Correção**: Removidos.

### 13. `_get_paths()` sem `return self` — `harvey_guy/harvey_guy.py`
**Problema**: Método de pipeline que não retornava `self`, violando `style.md` regra #1.
**Correção**: Adicionado `return self`.

---

## Problemas de Pipeline / Handoff (Corrigidos)

### 14. `SESSION_DIR` não definido explicitamente para subagentes — `harvey_guy/main.md`
**Problema**: Subagentes recebiam `SESSION_ID` e precisavam reconstruir `SESSION_DIR` por convenção — risco de variação.
**Correção**: `SESSION_DIR` agora definido explicitamente com a fórmula exata logo após captura do `SESSION_ID`.

### 15. Formato de `job.md` não especificado — `harvey_guy/main.md` + `harvey_guy/shadow.md`
**Problema**: O orchestrator escrevia `job.md` sem formato definido. Harvey Shadow tentava extrair o nome da empresa da "primeira linha" sem garantia de estrutura.
**Correção**: Formato obrigatório definido em Phase 1: `# <Position Title> — <Company Name>`. Shadow atualizado para parsear via `—` como separador garantido.

### 16. Fluxo de auth interativa do `agy` falha com output redirecionado — `karen_guard/run.sh`
**Problema**: O docker run de login interativo usa `-it`, mas `run.sh` é chamado com saída redirecionada. Se o usuário não estiver autenticado, o fluxo de login falha silenciosamente.
**Correção**: Documentado como pre-flight obrigatório em `harvey_guy/main.md` (Step 2) e `karen_guard/README.md`.

### 17. `race condition`: Harvey Shadow spawna antes de `job.md` estar em `SESSION_DIR` — iterações anteriores
**Problema**: Shadow lia `SESSION_DIR/docs/job.md` mas o arquivo só existia após `ingest_documents()` completar. Shadow poderia iniciar antes da cópia terminar.
**Correção**: Nota explícita no Step 1 que `job.md` e `cv.md` já estão copiados quando Shadow é spawado (Harvey Python roda sincronamente antes do spawn).

---

## Problemas de Documentação (Corrigidos)

### 18. `main.md` referenciava Phase errada — `main.md` (raiz)
**Problema**: Dizia "execute Phase 0: Initialize State" mas Phase 0 é "Dependency Verification" e Phase 1 é "Initialize State".
**Correção**: Texto corrigido para mencionar as duas phases corretamente.

### 19. `harvey_guy/README.md` descrevia tarefas do Harvey Shadow como do Harvey Python
**Problema**: README atribuía clonagem de repos, pesquisa de empresa, e build do Docker ao script Python — mas são do Shadow.
**Correção**: README reescrito separando claramente Harvey Python vs Harvey Shadow.

### 20. "Omie Tech Lead" hardcoded em `prompt_persona.txt`
**Problema**: Karen sempre mencionava "Omie Tech Lead" independentemente da vaga real passada pelo usuário.
**Correção**: Substituído por referência dinâmica ao `job.md`.

### 21. Git ausente das verificações em `requirements.md`
**Problema**: Git listado como dependência obrigatória em `harvey_guy/main.md` mas sem step de verificação correspondente.
**Correção**: Adicionada seção "Git Check" ao `requirements.md`.

### 22. `karen_guard/Readme.md` com nome inconsistente
**Problema**: Único README com letra minúscula em `eadme`, inconsistente com o resto do projeto.
**Correção**: Renomeado via `git mv` para `README.md`.

---

## Decisão de Arquitetura (Não-bug)

### 23. Restrição de `docs/who_are_u.md` por prompt (revertida)
**Contexto**: Sub-agente de revisão sugeriu adicionar restrição de prompt para Karen não ler `docs/who_are_u.md`. Foi aplicada e depois revertida.
**Decisão**: O isolamento é físico via volume Docker — quando `KAREN_READS_BACKGROUND=no`, o arquivo vai para `anti_karen/` que Karen não vê. Quando `yes`, Karen pode ler. Prompt restriction desnecessária e confusa.

---

## Reestruturação de Arquivos

| Antes | Depois | Motivo |
|---|---|---|
| `core.md` (raiz) | `harvey_guy/main.md` | Consistência com `karen_guard/main.md` e `billf/main.md` |
| `style.md` (guia Python) | `style.md` (guia de arquitetura de agentes) | Guia Python usado apenas para bootstrap inicial; não mais necessário |
| `karen_guard/Readme.md` | `karen_guard/README.md` | Consistência de nomenclatura |
