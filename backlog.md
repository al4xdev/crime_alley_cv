# Backlog — Actor-Critic CV Optimization Loop

Itens priorizados por impacto no funcionamento do core. P0 bloqueia a primeira execução real. P1 são gaps sérios pós-P0. P2 são features de expansão.

---

## P0 — Bloqueadores ✅ todos resolvidos

### ~~BLK-01: Feedback loop quebrado~~ ✅
CV de Bill agora é copiado de volta para `data/docs/cv.md` no Step 3 (Action 4) antes de reiniciar o loop. SANDBOXING RULE atualizada para documentar as duas modificações autorizadas a esse arquivo.

### ~~BLK-02: `KAREN_READS_BACKGROUND` nunca injetada no subprocess~~ ✅
Comando em Step 1 agora é `KAREN_READS_BACKGROUND=$VAL uv run python harvey_guy/main.py`.

### ~~BLK-03: `FIT_SCORE` sem fallback~~ ✅
Step 2 Action 5: se score não for extraível, loop para e reporta ao usuário com path do relatório para inspeção manual.

---

## P1 — Gaps Sérios ✅ todos resolvidos

### ~~GAP-01: `company_info.md` nunca consumido~~ ✅
Karen agora lê `company_info.md` antes de avaliar (instrução 0 no `prompt_persona.txt`). Shadow atualizado com estrutura obrigatória do arquivo e nota de que Karen o consome.

### ~~GAP-02: GitHub API sem autenticação~~ ✅
Shadow Step 2 usa apenas a API pública sem token (intencional — a avaliação deve refletir o que é visível publicamente). Repos públicos não precisam de auth para clonar. Se houver erro (rate limit, user não encontrado), Shadow reporta ao orchestrator e para. Contagem esperada salva e validada após os clones.

### ~~GAP-03: Estado do orchestrator sem checkpoint~~ ✅
Checkpoint escrito em `/tmp/karen_guard_loop_state.json` no início de cada Step 1 e atualizado após cada Bill revision no Step 3.

### ~~GAP-04: Saída silenciosa do loop~~ ✅
Gatekeeper emite Exit Report formatado ao usuário em ambas as condições de saída (score atingido / max loops), mostrando score final, iterações executadas e motivo.

### ~~GAP-05: Harvey Shadow rebuilda Docker em toda iteração~~ ✅
Shadow Step 4 agora faz `docker image inspect karen_guard` antes do build e pula se a imagem já existe.

---

## P2 — Novas Features

### ~~FEAT-01: Vera — Agente de onboarding para `who_are_u.md`~~ ✅
Criado `vera_guy/main.md` + `README.md`. Roleplay estruturado que produz `data/docs/who_are_u.md`. Roda em Phase 1.5 do `harvey_guy/main.md`, **opcional**: se o arquivo já existe, o orchestrator pergunta `reuse`/`refresh` — reuse pula Vera (fast path), refresh roda Vera em `MODE=refresh` aproveitando o arquivo existente. Adicionado às rosters de `main.md` e `README.md`, e à seção de support agents do `style.md`.

### ~~FEAT-02: Donna — Coach pós-loop com plano de ação~~ ✅
Criado `donna_guy/main.md` + `README.md`. Lê o relatório final da Karen e produz `data/docs/action_plan.md` (gaps técnicos priorizados, prep de entrevista, projetos públicos a criar). Invocada na seção "Post-Loop Coaching" do `harvey_guy/main.md`, em ambas as saídas do Gatekeeper. Inputs: `SESSION_ID`, `KAREN_REPORT_PATH`, `FIT_SCORE`, `MIN_FIT_SCORE`. Adicionada às rosters e ao `style.md`.

---

### FEAT-03: Harvey Shadow — Pesquisa de empresa mais rica

**Pré-requisito**: GAP-01 resolvido ✅ — Karen já consome `company_info.md`.

**Melhoria**: Ampliar Step 3 do `harvey_guy/shadow.md` para incluir:
- Tamanho da empresa (número de funcionários, funding se disponível)
- Stack tecnológica pública (GitHub da empresa, posts técnicos, job descriptions abertas)
- Cultura (valores declarados, Glassdoor se acessível via curl)
- Vagas abertas recentes relacionadas à posição (busca via DuckDuckGo: `<company> site:linkedin.com OR site:gupy.io vagas`)
- Notícias relevantes dos últimos 6 meses

**Implementação**: Atualizar Step 3 do `harvey_guy/shadow.md` com queries mais específicas. A estrutura do `company_info.md` já está definida em seções (Perfil, Stack, Cultura, Vagas, Notícias) — apenas enriquecer as queries.

**Nota**: "Vagas abertas" via APIs como LinkedIn requer autenticação. Usar DuckDuckGo com queries direcionadas é o caminho mais simples sem auth.

---

## Status Geral

```
BLK-01 ✅  BLK-02 ✅  BLK-03 ✅   (loop funcional)
GAP-01 ✅  GAP-02 ✅  GAP-03 ✅   (robustez operacional)
GAP-04 ✅  GAP-05 ✅

FEAT-01 (Vera)  ✅  FEAT-02 (Donna) ✅
FEAT-03 (Shadow+) ⏳ próxima sprint
```
