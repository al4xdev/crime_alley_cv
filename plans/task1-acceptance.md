# Aceitação final — Task 1

**Data:** 2026-07-15
**Veredicto:** **não aceita; resta um blocker concreto.**

## Blocker

### Alta — Donna pode violar seu contrato de único output e ainda concluir o run

- O contrato diz que o único alvo gravável de Donna é `.data/docs/action_plan.md` e proíbe alterar
  CV, job, avaliação, código ou repositórios (`donna_nana/main.md:23-27`).
- `prepare_donna` registra somente o snapshot anterior de `action_plan.md`
  (`harvey_guy/pipeline.py:946-968`). `complete_donna` valida somente esse plano e o digest do guard;
  não compara nenhum dos inputs declarados read-only (`harvey_guy/pipeline.py:997-1037`).
- Portanto Donna pode modificar, por exemplo, o CV, o job ou a avaliação final, criar um plano novo
  e obter `phase=complete`. Os testes de Donna cobrem plano stale, adulteração do guard e symlink de
  ancestral, mas não mutação dos inputs proibidos (`tests/test_pipeline.py:544-633`).

## Fechamento dos pareceres anteriores

- `task1-critic-1.md`: recovery/idempotência transacional, cobertura de Bill, frescor/arquivo de
  Donna, comando de replay e score ASCII estrito estão fechados.
- `task1-critic-2.md`: manifesto/payload/allowlist/revisão, digests canônicos dos guards, ancestrais
  e publicação validada de `.data/evaluation.md` estão fechados.
- Controle canônico por run, sessão fresca, isolamento dos roots de teste, replay offline e docs
  correspondentes foram confirmados.

## Checagens

- `uv run pytest -q tests/test_evaluation.py tests/test_harvey.py tests/test_pipeline.py tests/test_run_sh.py tests/test_render_instructions.py`: **42 passed**.
- `uv run ruff check harvey_guy tests tools`: **passou**.
- `uv run mypy harvey_guy tools/replay_pipeline.py`: **passou**.
