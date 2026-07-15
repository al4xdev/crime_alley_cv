# Auditoria forward-only do pipeline

**Data:** 2026-07-15
**Escopo:** branch `feat/boundaries-scripts`, execução offline e comparação com
`/home/alex/git/my/roleplay`.

## Veredicto

O conceito do projeto é bom: um evaluator-optimizer com isolamento explícito entre Karen e Bill,
e código determinístico nos pontos em que uma LLM pode falhar silenciosamente. A implementação da
branch, porém, distribui o estado autoritativo entre o contexto do orquestrador, um checkpoint em
`/tmp`, arquivos da sessão, códigos de saída e scripts Fish. As fronteiras detectam parte dos erros
depois da mutação, mas não são a dona transacional das mudanças.

A direção adotada nesta revisão é forward-only: um estado canônico por run, transições em Python,
eventos JSONL por run, artefatos versionados por iteração e adapters explícitos para execução real
ou replay. Os runbooks continuam responsáveis por julgamento e delegação; não serão responsáveis
por contadores, cópias, parsing ou persistência.

## Achados críticos

1. `CURRENT_LOOP` deixou de ser incrementado no runbook. `bill_harvey.fish` incrementa apenas o
   checkpoint, enquanto o orquestrador continua com o valor em contexto. Na iteração seguinte ele
   pode reinicializar o checkpoint para zero, impedindo `MAX_LOOPS` de encerrar o fluxo.
2. `pytest` executa `karen_guard/run.sh`, que copia o mock para `.data/evaluation.md`. A suíte
   sobrescreveu um artefato real com `Evaluation output` embora os 41 testes tenham passado.
3. O sandbox declara ausência de internet, mas o container tem rede e DNS; recebe uma cópia
   gravável de `.gemini`; executa `agy --dangerously-skip-permissions`; e o usuário interno possui
   `sudo NOPASSWD`. Prompt injection em repositório pode alcançar credenciais do provider.
4. O extrator de score aceita o primeiro `N/100` do relatório e não valida limites. Uma cobertura
   `99/100` anterior ao score vira o resultado; `140/100` também é aceito.
5. Harvey copia todos os arquivos de `anti_karen` da sessão anterior. Relatórios, warnings e
   snapshots stale podem satisfazer pós-condições de uma iteração nova.

## Achados altos

- A proteção de Bill usa apenas o conjunto de `git diff --name-only`: não detecta conteúdo alterado
  em arquivo que já estava dirty, arquivos untracked, mudanças staged nem adulteração do relatório
  de Karen.
- `harvey_shadow --post` passa se `repos_expected_count.txt` não existir. Warnings retornam zero e
  são registrados como `PASS`; código 2, reservado a uso inválido, é registrado como `WARNING`.
- O log `/tmp/boundary_audit.jsonl` é global, sujeito a colisões e só é persistido após Donna.
  Falhas antecipadas perdem justamente a evidência mais importante.
- A imagem `karen_guard` só é construída quando a tag não existe. Mudanças em Dockerfile, prompt ou
  evaluator podem nunca chegar ao runtime.
- O marker de dependências exige `Docker` e `wl-copy`, enquanto o contrato aceita Podman ou Docker e
  o container principal não instala `wl-copy`.
- Templates Jinja usam `Undefined` permissivo; placeholder divergente vira string vazia sem erro.
- Checkpoints usam redirecionamento destrutivo, sem lock, `fsync` ou rename atômico. Harvey engole
  qualquer erro de leitura do checkpoint.

## Evidência de validação

- `uv run pytest -q`: 41 passaram, mas com o efeito colateral em `.data/evaluation.md`.
- `fish -n boundaries/*.fish`: passou.
- `uv run ruff check .`: 19 erros.
- `uv run mypy harvey_guy`: 6 erros.
- O parser retornou `[99, 140, 55]` para casos ambíguos ou fora do intervalo.
- Há quatro relatórios e três revisões reutilizáveis em `.runs/20260710_120224/`; não existe
  `boundary_audit.jsonl` persistido nesse run.

## Padrões transferidos do roleplay

- estado canônico e paths configuráveis por ambiente;
- escrita JSON atômica com temporário, flush, `fsync` e replace;
- log JSONL append-only pertencente à sessão/run;
- isolamento obrigatório dos dados reais durante pytest;
- replay determinístico de respostas registradas;
- contratos estritos e falha em schema/placeholder desconhecido;
- adapters de provider fora do fluxo de domínio;
- imagem multi-stage, usuário sem privilégios e CI como contrato executável.

## Arquitetura-alvo

Cada run possui:

```text
.runs/<run-id>/
├── state.json
├── events.jsonl
├── scores.csv
└── iterations/<NN>/
    ├── cv_in.md
    ├── evaluation.md
    ├── evaluation.json
    ├── cv_out.md
    └── draft_notes.txt
```

`state.json` é a única fonte para fase, iteração, score, sessão atual e término. A CLI de pipeline
executa transições atômicas e emite JSON. O runbook só chama a CLI e delega Shadow, Karen, Bill e
Donna. O runtime de Karen é um adapter; nos testes ele é substituído por replay sem rede ou cota.

## Restrição temporária

Não há cota de `agy` disponível durante esta revisão. Nenhuma afirmação de ponta a ponta real será
feita. A entrega será validada por unit tests, testes de integração offline, replay, lint, tipos,
sintaxe dos scripts e inspeção independente em duas rodadas.

## Estado após a correção

- O estado canônico transacional, o limite de iterações e o parser estrito substituíram os
  checkpoints e parsers permissivos descritos acima.
- Cada sessão separa `anti_karen/artifacts`, `anti_karen/contracts/<agent>` e
  `anti_karen/logs`; uma sessão nova não herda saída privada anterior.
- Os scripts Fish voltaram como adapters finos: validam a fase, chamam uma única transição e
  persistem eventos com lock, validação e `fsync` em
  `.runs/<run-id>/logs/boundary_audit.jsonl`.
- `run_audit --finalize` mescla o journal do control plane e o audit das fronteiras, arquiva os
  artefatos/contratos/logs de todas as sessões e gera `log_tree.md` e `logs/pipeline.log`.
- O replay offline também percorre o run completo e produz a árvore final sem rede, `agy` ou dados
  reais do usuário.
