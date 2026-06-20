# Backlog — Actor-Critic CV Optimization Loop

O core (loop Actor-Critic + Vera/Donna) está estável e os itens planejados originais foram entregues e integrados ao container global.

> Princípio de design (decidido em sessão): migrar pro determinístico **apenas o que
> falha em silêncio**. O que falha alto, o agente cura sozinho — deixa na prosa.

---

## ✅ Concluído (sessão 2026-06-20)

### FIX: Karen lendo arquivos ocultos do diretório de docs (`harvey_guy.py`)
- **Causa**: `harvey_guy/harvey_guy.py` copiava todos os arquivos de `.data/docs/` para o sandbox, incluindo `.dependencies_checked.md` (gerado pelo pipeline de infra). A Karen lia esse arquivo, descobria o loop Actor-Critic e saía do seu escopo de avaliação.
- **Fix**: Adicionada verificação `if not item.name.startswith('.')` no loop de ingestão de documentos — arquivos ocultos são ignorados.
- **Validado**: `pytest` passando. Fix commitado em `harvey_guy/harvey_guy.py`.

---

## 🚀 Próximos Passos (A Fazer)

### TASK-02: Otimização de Consumo de Tokens Globais
- **Ignore Global (ex: `.agentignore`)**: Criar um mecanismo de ignore que filtre arquivos desnecessários (como `.lock`, arquivos de configuração de ferramentas, imagens, binários e dependências pesadas) para que **nenhum** agente (não apenas a Karen, mas todos os agentes do pipeline) consuma tokens lendo arquivos irrelevantes durante o processo.
- **Estratégias de Economia Global**: Pesquisar e planejar formas de otimização adicionais, como o uso de *Gemini Context Caching* para dados estáticos compartilhados (como os repositórios clonados e vaga) e telemetria básica para medir o consumo de tokens por iteração.

### TASK-11: Persistência de Camadas e Cache do Podman (Volume Mount)
- **Problema**: O build do sandbox `karen_guard` ocorre dentro do container orquestrador e leva de 4 a 6 minutos em cada execução inicial do pipeline, pois a pasta de storage do Podman (`/var/lib/containers`) é efêmera e reinicia limpa a cada `docker run` do container global.
- **Solução**: Modificar o script [start.sh](file:///home/alex/git/my/crime_alley_cv/start.sh) para montar um volume Docker nomeado persistente (ex: `-v crime_alley_podman_storage:/var/lib/containers`) no container global, fazendo com que as camadas de build do Podman persistam no host entre execuções do container global.

### TASK-12: Bug de Arquivamento Silencioso do loop_01 (Score Perdido + CSV Incompleto)
- **Problema**: Encontrado na auditoria do teste E2E. A run `20260620_210540` produziu 4 sessões com Karen:
  - `loop_00` (21:21): score=15, arquivado corretamente no `.runs`
  - `loop_01` (21:32): **score=45**, Karen rodou com sucesso, mas o orquestrador **não executou o bloco de arquivamento** (`cp cv.md`, `cp karen_report.md`, `echo >> scores.csv`). O score mais alto da run foi silenciosamente descartado.
  - `loop_02` (21:41): score=14, arquivado corretamente — mas a Karen avaliou um CV pior porque o Bill do loop_01 já havia removido habilidades que a Karen valorizava.
  - Resultado: o `scores.csv` vai `0,15 → 2,14`, pulando o loop 1. O pipeline rodou efetivamente 4 fases (Karen, Bill, Bill-sem-arquivamento, Karen) em vez de 3 bem definidas. O Gatekeeper tomou decisões com estado inconsistente.
- **Causa raiz provável**: O orquestrador (LLM) executou o Step 3 (Bill) sem antes concluir o bloco de arquivamento do Step 2 (linhas `ITER_DIR`, `cp`, `echo >> scores.csv`), possivelmente porque o contexto estava longo e o modelo "pulou" as instruções de persistência antes de chamar o Bill.
- **Solução**: Tornar o arquivamento **determinístico e não delegável ao LLM**. Extrair o bloco de arquivamento do `main.md` para um script shell (`harvey_guy/archive_loop.sh $SESSION_ID $CURRENT_LOOP $FIT_SCORE $RUN_DIR`) que o orquestrador apenas invoca. Um script não pode ser "esquecido" parcialmente — ou roda completo ou falha com erro visível.

### TASK-13: Zombie Processes de `conmon` Após Rodadas do Podman
- **Problema**: Encontrado no teste E2E. Após cada iteração do sandbox Karen, o processo `conmon` filho do Podman fica como `<defunct>` (zombie). O PID 1 do container global (fish/entrypoint) não faz `wait()` nesses filhos, acumulando dezenas de processos zombie ao longo de uma run completa. Não causa crash imediato, mas desperdiça entradas na tabela de processos.
- **Solução**: Usar `--init` no `docker run` do container global (via `start.sh`) para que um init mínimo (tini) seja o PID 1 e faça o reaping automático de processos zombie, ou chamar `podman wait` explicitamente no `run.sh` após cada invocação do sandbox.

---

### TASK-14: Scripts de Fronteira como Contratos Entre Agentes (Arquitetura)
> Esta é a próxima task grande. Generaliza o fix pontual da TASK-12 em um padrão arquitetural para todo o pipeline.

- **Problema**: Atualmente o orquestrador chama agentes e sub-agentes passando estado via instrução em prosa no prompt (`SESSION_ID`, `CURRENT_LOOP`, `FIT_SCORE`, `RUN_DIR`, etc.). O agente receptor lê, interpreta e age — mas não há garantia de que o estado de saída do agente anterior é válido e completo antes de o próximo começar. Quando o contexto está longo ou o modelo "pula" passos, o handoff falha em silêncio (como o loop_01 da TASK-12).

- **Conceito**: Toda transição entre agente A → agente B passa por um **script de fronteira** (`boundary_<a>_to_<b>.sh`) que:
  1. **Valida** o output do agente A (arquivos obrigatórios existem? score é parseable? CV não está vazio?).
  2. **Arquiva** o estado da iteração de forma atômica (tudo ou nada — se um `cp` falha, o script inteiro falha com exit ≠ 0).
  3. **Gera o input** do agente B: escreve um arquivo de contexto estruturado (`next_agent_ctx.json` ou variáveis de ambiente) que o agente B lê como primeira ação — sem depender de prosa do orquestrador.
  4. **Retorna exit code** que o orquestrador usa para decidir o próximo passo (sucesso, erro de validação, estado inconsistente).

- **Fronteiras a criar** (mapeando o fluxo atual):
  | Script | De | Para | Valida | Gera |
  |--------|----|------|--------|------|
  | `boundary_harvey_to_shadow.sh` | Harvey (setup) | Harvey Shadow | `SESSION_DIR` existe, `docs/` populado | `shadow_ctx.json` com `session_id`, `repos_url`, `company` |
  | `boundary_karen_to_gatekeeper.sh` | Karen Guard | Gatekeeper | `evaluation.md` existe, score parseable, `cv.md` não vazio | Arquiva `loop_NN/`, atualiza `scores.csv`, escreve `gatekeeper_ctx.json` |
  | `boundary_gatekeeper_to_bill.sh` | Gatekeeper | Bill | exit code 2 (continue), Karen report não vazio | `bill_ctx.json` com `session_id`, `karen_report_path`, `fit_score` |
  | `boundary_bill_to_loop.sh` | Bill | Próxima iteração | `cv.md` modificado, `draft_notes.txt` existe | Atualiza `loop_state.json`, faz carry-forward do CV para `.data/docs/cv.md` |

- **Benefício**: O orquestrador vira uma sequência de chamadas a scripts com exit codes — não um executor de instruções de prosa. Falhas são ruidosas por definição. Cada agente recebe um contrato estruturado como input, não um prompt longo com variáveis espalhadas.
- **Princípio**: Agentes decidem, scripts transitam. O LLM nunca deve ser responsável por persistência de estado entre dois agentes.
