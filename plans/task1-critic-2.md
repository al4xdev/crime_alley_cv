# Segundo parecer independente — Task 1

**Data:** 2026-07-15
**Escopo:** confiabilidade local, integridade dos arquivos do aplicativo, crash/retry e regressão dos
achados da primeira crítica. Revisão forward-only, sem exigir compatibilidade com interfaces
removidas.

## Veredicto

A rodada de correção resolveu os problemas visíveis da primeira crítica — parser ASCII estrito,
comando de replay documentado, cobertura ampliada de Bill, frescor/arquivo de Donna e recuperação
do crash antes de `state.json`. Ainda restam quatro falhas de engenharia no novo protocolo. As duas
primeiras são altas porque uma recuperação ou validação pode concluir com bytes ou baselines que o
próprio controle não autentica. A terceira permite que paths lexicalmente corretos apontem para
outro diretório sem o guard perceber. A quarta mantém um artefato canônico/fallback fora da
transação que valida a avaliação.

## Achados

### 1. Alta — recovery confia em manifesto, targets e payloads sem validar sua integridade

- **Evidência:** `_recover_pending` desserializa somente `manifest["writes"]` e ignora
  `schema_version`, `operation` e `revision` (`harvey_guy/pipeline.py:167-176`). Para cada entrada,
  valida apenas que o `source.resolve()` esteja sob `transactions/`; o `target` é aceito como path
  absoluto sem allowlist nem vínculo com a operação (`harvey_guy/pipeline.py:177-185`).
- **Evidência:** o manifesto registra apenas strings de source/target, sem tamanho ou SHA-256 do
  payload (`harvey_guy/pipeline.py:240-249`). Os payloads permanecem arquivos comuns graváveis nos
  diretórios de transação (`harvey_guy/pipeline.py:102-123`).
- **Lacuna de teste:** o único teste de recovery injeta falha imediatamente antes da cópia de
  `state.json`, mas conserva manifesto e payloads intactos (`tests/test_pipeline.py:240-286`). Não há
  casos de manifesto válido porém incoerente, target inesperado, payload alterado/ausente, revisão
  incompatível ou ordem de writes modificada.
- **Impacto em crash/retry:** depois de um crash com `pending.json`, uma alteração ou corrupção
  sintaticamente válida pode fazer o retry publicar conteúdo diferente do que foi staged, escrever
  no path incorreto ou aplicar `state.json` antes dos artefatos. Ainda assim o pending pode ser
  removido ao final (`harvey_guy/pipeline.py:185-186`), convertendo uma recuperação incompleta em
  estado aparentemente concluído.
- **Correção sugerida:** validar o manifesto com modelo estrito; vinculá-lo à revisão atual e à
  operação esperada; registrar e conferir SHA-256/tamanho de cada payload; exigir targets derivados
  de uma allowlist por operação; impor que `state.json` seja único e último. Só remover o pending
  após todas essas invariantes e os hashes pós-cópia passarem.

### 2. Alta — os guards de Bill e Donna confiam no próprio baseline mutável

- **Evidência:** `prepare_bill` grava todo o baseline em
  `guards/bill_<NN>.json` (`harvey_guy/pipeline.py:523-554`) e `commit_bill` aceita diretamente o
  JSON desse arquivo para comparar hash do CV, contexto protegido e worktree
  (`harvey_guy/pipeline.py:559-579`). O hash do guard não é mantido no estado, evento ou outro
  registro independente.
- **Evidência:** Donna repete o mesmo padrão: `prepare_donna` grava o snapshot anterior em
  `guards/donna.json` (`harvey_guy/pipeline.py:593-622`) e `complete_donna` confia nesse valor para
  decidir se o plano mudou (`harvey_guy/pipeline.py:627-643`). Ambos os loaders validam apenas que o
  JSON seja legível e contenha algumas chaves; não há modelo estrito nem autenticação do conteúdo.
- **Lacuna de teste:** os testes alteram inputs protegidos e confirmam a comparação contra um guard
  intacto (`tests/test_pipeline.py:289-349`) e verificam Donna contra um guard intacto
  (`tests/test_pipeline.py:352-378`). Não exercitam alteração, restauração parcial ou corrupção
  semântica do próprio baseline.
- **Impacto em crash/retry:** após recovery de `prepare-bill`/`prepare-donna`, uma modificação local
  no arquivo de guard pode produzir falso bloqueio ou falsa aceitação no retry seguinte. Como o
  estado apenas aponta para a fase e não ancora o digest esperado, não há como distinguir o
  baseline publicado pelo controle de outro JSON válido no mesmo path.
- **Correção sugerida:** persistir no estado/evento transacional o digest e a identidade do guard,
  validar o documento por schema estrito e conferir seu hash antes de qualquer comparação. Uma
  alternativa é incorporar o baseline ao próprio payload canônico de estado da revisão, eliminando
  a confiança em um arquivo solto.

### 3. Média — snapshots detectam symlink no leaf, mas não nos diretórios ancestrais

- **Evidência:** `_path_snapshot` chama `describe(path)` e `describe` verifica `is_symlink()` apenas
  no objeto recebido (`harvey_guy/pipeline.py:266-284`). Para os arquivos canônicos, o guard passa
  diretamente `data/docs/cv.md`, `job.md` e `who_are_u.md`, sem snapshot de `data/` ou `data/docs/`
  (`harvey_guy/pipeline.py:288-307`). O mesmo vale para os arquivos sob `session/docs/`.
- **Evidência:** a publicação do CV usa novamente o path lexical
  `state.data_path / "docs" / "cv.md"` (`harvey_guy/pipeline.py:581-587`). `atomic_copy` cria o
  temporário dentro de `destination.parent`, portanto segue qualquer symlink ancestral ainda
  presente (`harvey_guy/io.py:44-64`).
- **Lacuna de teste:** há um caso que troca o próprio `karen_output.md` por symlink, mas nenhum que
  troque `session/docs` ou `data/docs` mantendo arquivos-filho equivalentes
  (`tests/test_pipeline.py:289-325`).
- **Impacto em crash/retry:** se um diretório ancestral for substituído ou reconfigurado entre
  prepare e commit, os hashes e tipos dos filhos podem continuar iguais e o guard passa. O retry
  então lê ou publica o CV no diretório resolvido pelo link, embora estado, evento e docs registrem
  o path lexical original. Isso quebra a atribuição e a garantia de carregamento para `.data` sem
  exigir mudança de conteúdo nos arquivos protegidos.
- **Correção sugerida:** registrar tipo/identidade de todos os ancestrais controlados, resolver os
  roots uma vez e rejeitar mudança de resolução, além de abrir/copiar por descritores relativos com
  proteção contra symlinks (`openat`/`O_NOFOLLOW`) nos pontos de validação e publicação.

### 4. Média — `run.sh` publica a avaliação de conveniência antes do parser e fora da transação

- **Evidência:** ao encontrar qualquer `out/evaluation.md`, o wrapper move/copia o arquivo e
  sobrescreve `${PIPELINE_DATA_DIR}/evaluation.md` (`karen_guard/run.sh:148-154`). Só depois o
  runbook chama `record-evaluation` (`harvey_guy/main.md:75-93`), onde o parser estrito e o protocolo
  transacional finalmente são aplicados (`harvey_guy/pipeline.py:472-520`).
- **Evidência adicional:** Donna ainda documenta `.data/evaluation.md` como fallback de leitura
  (`donna_nana/main.md:15-18`), portanto a cópia não é apenas telemetria sem consumidor.
- **Lacuna de teste:** `test_run_sh_auth_success` gera literalmente `Evaluation output`, que não
  contém score canônico, e mesmo assim exige sucesso do script e a publicação desse texto no data
  dir (`tests/test_run_sh.py:40-54`, `tests/test_run_sh.py:70-83`). A integração não encadeia esse
  resultado inválido com `record-evaluation` nem verifica preservação do último relatório válido.
- **Impacto em crash/retry:** uma saída vazia semanticamente ou com score inválido pode substituir
  o último fallback válido; em seguida `record-evaluation` falha e mantém a fase, mas não restaura a
  cópia anterior. Crash entre a cópia e a transição deixa a mesma divergência. Um retry da avaliação
  parte com estado antigo e fallback novo, sem pending capaz de reconciliá-los.
- **Correção sugerida:** retirar a publicação em `.data` do wrapper. `record-evaluation` deve staged
  e publicar essa cópia somente depois de `read_evaluation` passar, no mesmo manifesto dos arquivos
  de iteração, scores, evento e estado. Donna deve consumir o relatório arquivado do run/iteração,
  não um fallback mutável.

## Checagem desta rodada

Revisão estática adversarial dos fluxos de transação/recovery, Bill, Donna, wrapper de Karen,
testes e documentação. Conforme solicitado, não foram feitas novas reproduções nesta etapa e nenhum
arquivo de código foi alterado.
