# Debug & State Tracking Map — Actor-Critic CV Loop

Este arquivo serve como o mapa de referência rápida para monitorar e depurar o estado do pipeline multi-agente dentro do container Docker.

---

## 📍 Localizações Críticas & Ciclo de Vida

### 1. Estado da Iteração Atual (Checkpoint)
- **Arquivo**: `/tmp/karen_guard_loop_state.json` (dentro do container)
- **Escrito por**: Harvey (Orquestrador) / Bill (Editor) ao final de cada iteração.
- **Estrutura**: `{"current_loop": X, "fit_score": Y, "session_id": "UUID"}`
- **Comando para inspecionar**:
  ```bash
  docker exec <container_name> cat /tmp/karen_guard_loop_state.json
  ```

### 2. Diretório de Sessão Isolado (Temporário)
- **Diretório**: `/tmp/karen_guard_<SESSION_ID>/` (dentro do container)
- **Criado por**: Harvey (Orquestrador) no início de cada execução.
- **Componentes**:
  - `docs/cv.md`: A versão do currículo que está sendo avaliada na iteração corrente.
  - `docs/job.md`: A descrição de cargo da vaga alvo.
  - `docs/who_are_u.md`: O perfil do candidato (presente apenas se `KAREN_READS_BACKGROUND=yes`).
  - `company_info.md`: O perfil de pesquisa da empresa gerado pelo `Harvey Shadow`.
  - `repos/`: Repositórios públicos clonados pelo `Harvey Shadow`.
  - `out/`: Diretório de saída montado para a `Karen Guard` escrever (deve estar vazio após a execução).

### 3. Zona Protegida (Anti-Karen)
- **Diretório**: `/tmp/karen_guard_<SESSION_ID>/anti_karen/` (dentro do container)
- **Objetivo**: Armazenar dados ocultos da Karen para evitar vazamentos/injeções de prompt.
- **Componentes**:
  - `karen_run.log` e `karen_run.err`: Logs brutos de execução da CLI `agy` da Karen.
  - `karen_output.md` / `evaluation.md`: O relatório técnico gerado pela Karen.
  - `karen_guard_core.log`: Logs gerais do script Harvey (`harvey_guy.py`).
  - `who_are_u.md`: O perfil do candidato (guardado aqui se `KAREN_READS_BACKGROUND=no`).
  - `draft_notes.txt`: Notas de rascunho de revisão escritas pelo Bill.

### 4. Arquivos Persistentes (Host / Mounts)
- **Diretório**: `.data/docs/` (persistido no host, montado em `/app/.data/docs/`)
  - `cv.md`: Currículo consolidado inicial/final.
  - `job.md`: Descrição da vaga alvo formatada.
  - `who_are_u.md`: Perfil de onboarding (Vera).
  - `action_plan.md`: Plano de ação final pós-loop (Donna).
- **Diretório**: `.runs/` (persistido no host, montado em `/app/.runs/`)
  - `<timestamp>/scores.csv`: Histórico do score por iteração.
  - `<timestamp>/loop_<XX>/`: Cópia integral de entrada/saída de cada loop para auditoria.

---

## 🛠️ Comandos de Monitoramento Rápido (No Host)

### Monitorar logs da Karen em tempo real
```bash
docker exec -it $(docker ps -lq) tail -f /tmp/karen_guard_loop_state.json 2>/dev/null || echo "Ainda não inicializado"
```

### Inspecionar árvore de arquivos da sessão ativa no container
```bash
docker exec -it $(docker ps -lq) tree -L 3 -a /tmp
```

### Verificar o progresso de execução e erros da Karen
```bash
docker exec -it $(docker ps -lq) cat /tmp/karen_guard_loop_state.json | jq -r '.session_id' | xargs -I {} docker exec -it $(docker ps -lq) tail -n 20 /tmp/karen_guard_{}/anti_karen/karen_run.err
```

### Validar se o currículo intermediário está mudando
```bash
docker exec -it $(docker ps -lq) cat /tmp/karen_guard_loop_state.json | jq -r '.session_id' | xargs -I {} docker exec -it $(docker ps -lq) diff -u /app/.data/docs/cv.md /tmp/karen_guard_{}/docs/cv.md
```
