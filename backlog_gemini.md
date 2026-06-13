# Gemini Orchestrator — Backlog

> Planejamento das capacidades cognitivas do orquestrador Gemini.
> Este documento guia o ensino e comportamento do agente orquestrador global.

---

> [!IMPORTANT]
> **AVISO DE UX / AUTOPREENCHIMENTO:**
> Devemos treinar e instruir o orquestrador Gemini para preencher e preparar de forma autônoma toda a estrutura de dados e arquivos de contexto para o usuário.
> O usuário não deve ter o atrito de configurar caminhos manuais, preencher templates vazios ou deduzir quais informações colocar. O Gemini deve gerar rascunhos proativos de briefing, CV adaptado, cartas de apresentação e configurações do Karen Guard, deixando para o usuário apenas a revisão final.

---

## Próximas entregas do Orquestrador Gemini

### 1. Ingestão de Contexto e Autopreenchimento (Alta Prioridade)
- [ ] Analisar os repositórios clonados na pasta `data/repos/` para extrair perfil de desenvolvedor sênior (projetos, stacks e padrões de código).
- [ ] Ler arquivos do sistema e gerar automaticamente o rascunho de `data/documentation/briefing.md` baseando-se no histórico profissional do usuário.
- [ ] Detectar a empresa atual e experiências passadas de forma inteligente.

### 2. Orquestração e Pipelines
- [ ] Permitir disparar o pipeline completo `Core` -> `Adaptação de CV` -> `Karen Guard (Docker)` através de comandos em linguagem natural no chat.
- [ ] Consolidar relatórios de múltiplas vagas na pasta `vagas/`.

### 3. Integração Inteligente com o Karen Guard
- [ ] Preparar a pasta temporária de entrada do Karen Guard (`/tmp/karen_guard_<timestamp>/`).
- [ ] Ler o `evaluation.md` e gerar planos de ação específicos sobre como ajustar o currículo ou quais tópicos técnicos revisar antes de entrevistas reais.
