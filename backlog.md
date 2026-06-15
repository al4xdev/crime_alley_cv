# Backlog — Actor-Critic CV Optimization Loop

Itens priorizados por impacto no funcionamento do core. P0 bloqueia a primeira execução real. P1 são gaps sérios pós-P0. P2 são features de expansão.

---

## P0 — Bloqueadores (o loop não funciona sem isso)

### BLK-01: Feedback loop quebrado — CV de Bill nunca chega à próxima iteração

**Problema**: `harvey_guy.py` gera um novo `uuid4()` em cada chamada. A cada iteração do loop, um novo `SESSION_DIR` é criado. `ingest_documents()` copia sempre de `data/docs/cv.md` (original). O CV revisado por Bill em `SESSION_DIR_N/docs/cv.md` nunca é passado para a iteração N+1. Karen avalia o CV original em toda iteração.

**Impacto**: Qualquer run com `MAX_LOOPS > 1` produz lixo. O loop não converge por design.

**Implementação**:
Opção A (simples — mudança no runbook): adicionar instrução no Gatekeeper de que, antes de incrementar `CURRENT_LOOP` e reiniciar o Step 1, o orchestrator deve copiar `SESSION_DIR/docs/cv.md` para `data/docs/cv.md`. A SANDBOXING RULE já tem exceção para exit — estender para o handoff inter-iteração.

Opção B (mais robusta — mudança no Python): `harvey_guy/main.py` aceita argumento opcional `--previous-cv <path>`. Se fornecido, `ingest_documents()` copia o CV desse path em vez de `data/docs/cv.md`. O orchestrator passa o path da iteração anterior.

**Recomendação**: Opção A para a v1 (zero mudança de código, apenas runbook). Opção B quando o core estiver estável.

---

### BLK-02: `KAREN_READS_BACKGROUND` nunca injetada no subprocess

**Problema**: O orchestrator armazena a resposta do usuário como variável em contexto, mas não há instrução para prefixar o `uv run` com a variável de ambiente. `harvey_guy.py` usa `os.environ.get("KAREN_READS_BACKGROUND", "yes")` — sempre defaulta para `"yes"`. Quando o usuário responde "no", `who_are_u.md` ainda vai para `session/docs/` e Karen lê o background que deveria ser cego para ela.

**Implementação**: Uma linha no runbook em Phase 1 (Initialization Actions) e Step 1:
```bash
KAREN_READS_BACKGROUND=no uv run python harvey_guy/main.py
# ou "yes" conforme resposta do usuário
```
Nenhuma mudança de código necessária.

---

### BLK-03: `FIT_SCORE` sem fallback — gatekeeper sem comportamento definido em falha

**Problema**: Se Gemini reformatar o heading, usar capitalização diferente, ou não produzir score (recusa, truncamento), `FIT_SCORE` fica indefinido. O gatekeeper não tem instrução para esse caso. O loop pode iterar indefinidamente com score nulo, ou o orchestrator pode interpretar `""` como `0` e nunca sair.

**Implementação**: Adicionar ao Gatekeeper em `harvey_guy/main.md`:
> Se `FIT_SCORE` não puder ser extraído do relatório (linha `## Technical Fit Score:` ausente ou malformada), tratar como falha crítica: reportar ao usuário, mostrar o path do `karen_output.md` para inspeção manual, e interromper o loop.

---

## P1 — Gaps Sérios (executar após P0)

### GAP-01: `company_info.md` nunca consumido por nenhum agente

**Problema**: Harvey Shadow passa tempo pesquisando a empresa e escrevendo `company_info.md` em `SESSION_DIR`. Karen tem acesso ao arquivo via volume Docker, mas seu `prompt_persona.txt` não instrui ela a lê-lo. Nenhum outro agente o referencia. O trabalho é descartado em cada iteração.

**Implementação**: Adicionar ao `prompt_persona.txt` de Karen (seção de Evaluation Instructions), antes do item 1:
> **0. COMPANY CONTEXT**: Before evaluating, read `company_info.md` if present in the session directory. Use it to understand the company's tech stack, culture, and priorities — this context should inform how you weight technical gaps and highlight relevant strengths.

Também adicionar ao `harvey_guy/shadow.md` Step 3 que `company_info.md` é consumido por Karen — para que o Shadow saiba que sua pesquisa tem impacto real.

---

### GAP-02: GitHub API sem autenticação — rate limit em perfis grandes

**Problema**: Shadow usa a API pública do GitHub (60 req/hora sem token). Perfis com 30+ repos podem ser truncados. Falhas individuais de `git clone` dentro do `xargs -P 5` são silenciosas — o orchestrator verifica que `repos/` "está populado" mas não sabe quantos repos falharam.

**Implementação**:
1. Adicionar ao `harvey_guy/shadow.md` Step 2: verificar se `GITHUB_TOKEN` está disponível no ambiente e usar `Authorization: Bearer $GITHUB_TOKEN` no curl se presente.
2. Adicionar checagem por repo após o `xargs`: `ls SESSION_DIR/repos/ | wc -l` vs contagem esperada do JSON — reportar discrepância.
3. Adicionar ao `requirements.md`: recomendar configuração de `GITHUB_TOKEN` para perfis com muitos repos.

---

### GAP-03: Estado do orchestrator sem checkpoint — qualquer reset perde tudo

**Problema**: `CURRENT_LOOP`, `FIT_SCORE`, `SESSION_ID`, `KAREN_REPORT_PATH` existem apenas no contexto do orchestrator. Um reset de contexto, erro de modelo, ou atingimento de limite de tokens no meio do loop perde todo o estado. Não há como retomar.

**Implementação**: Adicionar ao início de cada iteração do loop uma instrução no runbook para o orchestrator escrever um checkpoint:
```bash
# Escrever em SESSION_DIR/anti_karen/loop_state.json:
{
  "current_loop": N,
  "fit_score": X,
  "session_id": "...",
  "karen_report_path": "..."
}
```
Em caso de retomada, o orchestrator lê esse arquivo para restaurar o estado.

---

### GAP-04: Saída silenciosa do loop — nenhuma notificação ao usuário

**Problema**: Quando o gatekeeper dispara a saída (por score ou por max loops), o runbook instrui apenas a copiar o CV de volta ao repo. Não há instrução para notificar o usuário do resultado, mostrar o score final, ou explicar por que o loop terminou.

**Implementação**: Adicionar seção "Exit Report" ao Gatekeeper em `harvey_guy/main.md`:
> Ao sair do loop, exibir ao usuário: score final, número de iterações executadas, motivo da saída (score atingido / max loops), e o path do relatório final em `data/evaluation.md`.

---

### GAP-05: Harvey Shadow rebuilda Docker em toda iteração

**Problema**: Shadow faz `docker build` em todo Step 1, mesmo que a imagem já exista. `run.sh` já tem o guard `docker image inspect` (skip se existe), mas Shadow não. Resultado: build desnecessário em toda iteração N > 1.

**Implementação**: Adicionar ao `harvey_guy/shadow.md` Step 4, antes do build:
```bash
if docker image inspect karen_guard >/dev/null 2>&1; then
  echo "karen_guard image already exists, skipping build."
  exit 0
fi
```

---

## P2 — Novas Features (expandir após core estável)

### FEAT-01: Vera — Agente de onboarding para `who_are_u.md`

**Contexto**: `who_are_u.md` é a fonte de verdade do Bill (anti-alucinação), mas não existe processo para criá-la. O usuário deve criar manualmente — o que raramente acontece.

**Papel**: Agente de roleplay que conduz uma conversa estruturada com o usuário, fazendo perguntas abertas sobre carreira, forma de pensar, liderança e valores. Ao final, salva `data/docs/who_are_u.md`.

**Quando roda**: Standalone, antes da primeira execução do loop principal. Não faz parte do loop iterativo.

**Implementação**:
- Criar `vera_guy/main.md` seguindo o padrão (inputs, isolamento, plano step-by-step)
- Entradas: nenhuma (conversa livre com o usuário)
- Saída: `data/docs/who_are_u.md`
- Adicionar ao `main.md` raiz como pré-requisito opcional mas recomendado antes do loop
- Adicionar linha na Agent Roster table do `README.md`

**Estrutura do diálogo sugerida**:
1. Histórico profissional (empresas, cargos, anos)
2. Projetos mais relevantes (tecnologias, escala, impacto)
3. Estilo de trabalho e liderança
4. Certificações e formação verificada
5. Valores e motivações de carreira

---

### FEAT-02: Donna — Coach pós-loop com plano de ação

**Contexto**: O loop termina com um CV otimizado, mas o candidato também precisa saber o que desenvolver para subir seu score nas próximas tentativas.

**Papel**: Agente coach que lê o `evaluation.md` final e produz `data/docs/action_plan.md` com: gaps técnicos a fechar, tópicos para revisar antes de entrevistas, e projetos públicos a criar ou melhorar para aumentar o score Karen.

**Quando roda**: Após o loop principal, invocado pelo orchestrator na saída (Exit Report).

**Implementação**:
- Criar `donna_guy/main.md` com estrutura padrão
- Entradas: `SESSION_ID`, `KAREN_REPORT_PATH`, `FIT_SCORE`, `MIN_FIT_SCORE`
- Saída: `data/docs/action_plan.md`
- Adicionar ao Gatekeeper em `harvey_guy/main.md`: após copiar o CV final, spawnar Donna com os inputs acima
- Adicionar linha na Agent Roster table do `README.md`

**Estrutura do `action_plan.md` sugerida**:
1. Score atingido vs. meta
2. Gaps técnicos identificados (com prioridade)
3. Tópicos para estudar antes da entrevista
4. Projetos públicos a criar ou melhorar (com sugestões concretas)
5. Próximos passos ordenados por impacto

---

### FEAT-03: Harvey Shadow — Pesquisa de empresa mais rica

**Pré-requisito**: Resolver GAP-01 (`company_info.md` sendo consumido por Karen) primeiro. Sem isso, melhorar a pesquisa não tem efeito.

**Melhoria**: Ampliar Step 3 do `harvey_guy/shadow.md` para incluir:
- Tamanho da empresa (número de funcionários, funding se disponível)
- Stack tecnológica pública (GitHub da empresa, posts técnicos, job descriptions abertas)
- Cultura (valores declarados, Glassdoor se acessível via curl)
- Vagas abertas recentes relacionadas à posição (busca via DuckDuckGo: `<company> site:linkedin.com OR site:gupy.io vagas`)
- Notícias relevantes dos últimos 6 meses

**Implementação**: Atualizar Step 3 do `harvey_guy/shadow.md` com queries mais específicas e estrutura do `company_info.md` em seções (Perfil, Stack, Cultura, Vagas, Notícias).

**Nota**: "Vagas abertas" via APIs como LinkedIn requer autenticação. Usar DuckDuckGo com queries direcionadas é o caminho mais simples sem auth.

---

## Ordem de Implementação Recomendada

```
BLK-01 → BLK-02 → BLK-03   (loop funcional)
         ↓
GAP-01 → GAP-04             (Karen usa company_info, exit com relatório)
GAP-02 → GAP-03 → GAP-05   (robustez operacional)
         ↓
FEAT-01 (Vera)              (onboarding — antes do loop)
FEAT-02 (Donna)             (coaching — após o loop)
FEAT-03 (Shadow upgrade)    (depende de GAP-01 estar resolvido)
```
