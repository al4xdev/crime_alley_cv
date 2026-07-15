# Parecer independente — Task 1

**Data:** 2026-07-15
**Escopo:** plano de controle por run, parser de score, frescor das sessões, integridade de Bill,
isolamento de dados em testes, replay offline e documentação associada. Revisão forward-only; as
interfaces removidas não foram tratadas como requisito.

## Veredicto

A direção arquitetural está correta e as checagens existentes passam, mas a Task 1 ainda não cumpre
integralmente o contrato anunciado. Há três falhas altas: a transição durável envolve vários arquivos
sem commit/recovery transacional; o guard de Bill mede o repositório errado e deixa fontes alcançáveis
sem proteção; e Donna pode concluir um run com o `action_plan.md` de um run anterior. O replay
automatizado funciona pelo módulo, porém o comando publicado ao usuário não funciona.

## Achados

### 1. Alta — transições não são atômicas nem idempotentes entre estado, journal e artefatos

- **Evidência:** `RunStore.transition` grava primeiro `state.json` e só depois acrescenta o evento
  (`harvey_guy/pipeline.py:118-143`). Se o append de `events.jsonl` falhar, a fase já avançou; uma
  repetição do comando é recusada pela nova fase e o journal fica definitivamente incompleto.
- **Evidência:** `record_evaluation` copia três artefatos e acrescenta `scores.csv` antes de o
  `RunStore` persistir a nova revisão (`harvey_guy/pipeline.py:306-342`). Uma falha depois da linha de
  score e antes do estado deixa `iterations/<NN>` e/ou uma linha de score para uma avaliação que o
  estado ainda não contabiliza. Ao repetir, os arquivos são sobrescritos e a linha de score é
  duplicada.
- **Evidência adicional:** `commit_bill` arquiva `cv_out.md`, notas e substitui o CV canônico antes do
  commit do estado (`harvey_guy/pipeline.py:384-421`). `initialize_run` cria o diretório do run antes
  de validar `max_iterations`/`min_fit_score` via `RunState` (`harvey_guy/pipeline.py:211-230`), então
  entrada inválida deixa um run órfão que impede retry com o mesmo ID.
- **Divergência documental:** o plano exige “transições atômicas”
  (`plans/2026-07-15-forward-only-audit.md:90-92`) e `style.md` promete que a transição é completa ou
  não avança (`style.md:38-40`). Escrita atômica de cada arquivo isolado não torna o conjunto
  transacional.
- **Impacto:** após falta de espaço, interrupção ou erro de I/O, `state.json`, `events.jsonl`,
  `scores.csv`, arquivo de iteração e `.data/docs/cv.md` podem discordar. O histórico deixa de provar
  quantas avaliações ocorreram e o run pode ficar sem retry seguro.
- **Correção sugerida:** introduzir um ID de transição e protocolo recuperável (write-ahead
  `pending`/`committed`, ou staging completo mais um manifesto/ponteiro canônico substituído
  atomicamente). Tornar scores e eventos deriváveis/idempotentes por revisão, nunca por append cego,
  e validar todos os argumentos antes de criar o diretório. Adicionar testes de injeção de falha após
  cada escrita e de retry/recovery.

### 2. Alta — o guard de Bill não protege os repositórios da sessão nem as fontes canônicas em `.data`

- **Evidência:** `_repository_snapshot()` fixa o alvo em `REPOSITORY_ROOT` e executa `git ls-files`
  no repositório deste projeto (`harvey_guy/pipeline.py:163-180`). `prepare_bill` e `commit_bill`
  usam esse snapshot (`harvey_guy/pipeline.py:345-410`), mas não calculam hashes de
  `$SESSION_DIR/repos`, `repos.json` ou `repos_expected_count.txt`.
- **Evidência adicional:** o guard protege as cópias de job/background dentro da sessão, não os
  arquivos-fonte em `state.data_path`. `.data/` é explicitamente ignorado pelo Git (`.gitignore:12-19`),
  portanto alterações em `.data/docs/job.md` ou `.data/docs/who_are_u.md` também não aparecem no
  snapshot genérico do host.
- **Contrato/teste insuficiente:** Bill é proibido de escrever nos repositórios clonados
  (`billf/main.md:21-27`) e o README afirma que nenhum “repository file” pode mudar (`README.md:45-53`),
  mas o único teste negativo altera apenas `karen_output.md` (`tests/test_pipeline.py:150-174`).
- **Impacto:** Bill pode alterar/adicionar/remover código de evidência na sessão, adulterar o
  inventário ou modificar os inputs que alimentarão a próxima sessão e ainda assim `commit-bill`
  aceita e carrega o CV. O guard dá uma garantia diferente da documentada.
- **Correção sugerida:** guardar recursivamente os artefatos realmente alcançáveis e proibidos:
  repositórios e inventário da sessão, fontes canônicas de job/background e demais inputs do run,
  registrando também tipo/symlink/ausência. Melhor ainda, executar Bill numa fronteira com apenas o
  CV e `anti_karen` graváveis. Incluir testes para alteração, criação, remoção e troca por symlink em
  cada classe protegida.

### 3. Alta — `complete-donna` aceita saída histórica e o run não preserva seu action plan

- **Evidência:** `prepare_donna` não remove nem registra hash/mtime do action plan existente
  (`harvey_guy/pipeline.py:424-444`). `complete_donna` aceita qualquer
  `.data/docs/action_plan.md` com 100 bytes e um heading (`harvey_guy/pipeline.py:447-457`).
  `initialize_run` também não neutraliza a saída do run anterior.
- **Evidência de cobertura:** o teste feliz sempre escreve um novo arquivo imediatamente antes de
  concluir (`tests/test_pipeline.py:111-116`); não há caso com um `action_plan.md` preexistente e
  Donna sem produzir saída.
- **Impacto:** se Donna falhar silenciosamente, um plano antigo satisfaz a pós-condição e o run é
  marcado `complete`. Além disso, o evento aponta para o arquivo mutável em `.data`; o próximo run
  pode sobrescrevê-lo, eliminando o plano atribuível ao run concluído.
- **Correção sugerida:** no prepare, registrar a ausência/hash inicial (ou mover de forma segura a
  saída antiga); no complete, exigir criação ou mudança posterior ao prepare e copiar atomicamente o
  resultado para o diretório do run antes de avançar a fase. Testar saída stale, ausente, inalterada
  e nova.

### 4. Média — o comando de replay documentado falha; o teste exercita outra interface

- **Evidência:** README e Harvey README publicam `uv run python tools/replay_pipeline.py`
  (`README.md:75-84`, `harvey_guy/README.md:41-52`). Executado a partir da raiz, esse comando falha
  em `tools/replay_pipeline.py:11` com `ModuleNotFoundError: No module named 'harvey_guy'` porque o
  diretório do script, não a raiz, entra em `sys.path`.
- **Evidência de cobertura:** o teste usa `python -m tools.replay_pipeline`
  (`tests/test_pipeline.py:196-219`), que funciona e, portanto, não valida o comando publicado.
- **Impacto:** o caminho recomendado para replay offline não inicia, embora a suíte passe.
- **Correção sugerida:** documentar e testar `uv run python -m tools.replay_pipeline` (preferível) ou
  fornecer um entry point instalável/robusto e testar exatamente o comando do README.

### 5. Baixa — o parser “estrito” aceita algarismos Unicode fora do formato documentado

- **Evidência:** o regex usa `\d{1,3}` (`harvey_guy/evaluation.py:9-12`); em Python, `\d` aceita
  dígitos Unicode. Por exemplo, `## Technical Fit Score: ٧٢/100` é aceito e resulta em 72. Os testes
  cobrem ambiguidade, score fora da faixa e ausência do heading, mas não o alfabeto numérico
  (`tests/test_evaluation.py:8-26`).
- **Impacto:** pequeno desvio do contrato de uma linha canônica interoperável; consumidores que
  esperem ASCII podem divergir do parser.
- **Correção sugerida:** usar `[0-9]{1,3}` e adicionar o caso Unicode à parametrização negativa.

## Pontos que foram comprovados

- O parser seleciona exatamente uma linha canônica e rejeita duplicidade, ausência de heading e
  valor maior que 100 nos casos atuais.
- Harvey cria UUID e sessão nova e ingere apenas CV, job e background configurado; action plan e
  drafts anteriores não entram na sessão.
- `tests/conftest.py` configura roots temporários antes dos imports, e os testes inspecionados não
  tocaram a `.data` real.
- O replay pelo módulo (`python -m tools.replay_pipeline`) percorre três avaliações sem `agy` e sem
  quarta sessão.

## Checagens executadas

- `uv run pytest -q tests/test_evaluation.py tests/test_harvey.py tests/test_pipeline.py tests/test_run_sh.py`:
  **16 passed**.
- `uv run ruff check harvey_guy tests tools`: **passou**.
- `uv run mypy harvey_guy tools/replay_pipeline.py`: **passou**.
- Reprodução manual do comando documentado: **falhou** com `ModuleNotFoundError`.
- Reprodução do score Unicode: **aceito como 72**.
