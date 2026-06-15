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

FEAT-01 (Vera)    ⏳ próxima sprint
FEAT-02 (Donna)   ⏳ próxima sprint
FEAT-03 (Shadow+) ⏳ próxima sprint
```
