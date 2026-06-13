# Karen Guard & Job-Stack — Backlog

> Único documento de planejamento do projeto.
> O que não está implementado vive aqui.

---

## Arquitetura alvo (Simplificada)

```
meta_2028/
├── docs/                        ← briefing.md, cv_base.md e retrospectivas
├── repos/                       ← clones/cópias dos repositórios públicos
└── karen_guard/
    ├── Dockerfile               ← define o ambiente isolado
    ├── run.sh                   ← script para subir o container com volumes
    └── evaluator.py             ← avaliador (script Python consumindo APIs de LLM)
```

---

## Fluxo simplificado (Foco Inicial)

```
1. Preparar o container Docker do Karen Guard
2. Subir o container de forma interativa / ativa
3. Entrar no container junto com o usuário para testar e validar autenticação
4. Executar avaliação apontando para os repos locais montados como volume
```

---

## Backlog de tasks

### Fase 1: Karen Guard & Ambiente Docker (Alta Prioridade)
- [ ] Criar o `Dockerfile` inicial do Karen Guard (Python + dependências necessárias)
- [ ] Criar o script `run.sh` para build e execução interativa (com montagem de volumes para repos e chaves)
- [ ] Testar e validar autenticação (exploração interativa do Gemini/Claude dentro do Docker)
- [ ] Implementar script básico de avaliação (`evaluator.py`) rodando dentro do container

### Fase 2: Estrutura do Workspace e Integração
- [ ] Criar estrutura de pastas do projeto (`docs/`, `repos/`)
- [ ] Organizar o fluxo de montagem do workspace em `/tmp/karen_guard_<timestamp>/`
- [ ] Implementar a geração automática do relatório de avaliação (`evaluation.md`)

### Fase 3: Adaptação de CV e MCP
- [ ] Implementar o script/CLI de adaptação de CV
- [ ] Criar o servidor MCP de contexto para servir `docs/` ao Antigravity CLI no host

---

## Fora de escopo (Decidido)

- **Anonimização de CV**: Removida do escopo para simplificação técnica e foco na isolação pura do container.
- **LinkedIn/Browser Automation**: Apenas curadoria manual.