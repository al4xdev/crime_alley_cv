# Reaceitação final — Task 1

**Data:** 2026-07-15
**Veredicto:** **ACEITA**

## Blocker de integridade da Donna

O blocker foi fechado no contrato auditado:

- `DonnaGuard` agora registra snapshots do contexto protegido e do worktree, com digest ancorado
  no estado canônico (`harvey_guy/pipeline.py:95-102`, `harvey_guy/pipeline.py:971-986`).
- O conjunto protegido inclui as cópias de CV e job da sessão e canônicas, os repositórios da
  sessão e a avaliação final arquivada (`harvey_guy/pipeline.py:623-634`).
- `complete_donna` autentica o guard e recusa mudanças nesses inputs ou no repositório host antes
  de concluir o run (`harvey_guy/pipeline.py:1025-1046`). Continua exigindo plano novo ou alterado
  e o arquiva por run (`harvey_guy/pipeline.py:1047-1064`).
- A regressão negativa cobre mutação de CV, job, avaliação final, repositório da sessão e
  worktree, sempre mantendo a fase em `donna_running` (`tests/test_pipeline.py:608-656`).

## Regressão curta dos contratos da Task 1

- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_evaluation.py tests/test_harvey.py tests/test_pipeline.py tests/test_run_sh.py tests/test_render_instructions.py`: **47 passed**.
- A inspeção focada não encontrou blocker concreto nos contratos forward-only da Task 1.
- Sandbox, credenciais, rede e compatibilidade com o legado ficaram fora do escopo desta
  reaceitação.
