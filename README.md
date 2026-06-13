# Job-Stack & Karen Guard

Orquestrador e avaliador de candidaturas automatizadas baseado em uma arquitetura multi-agente Actor-Critic.

## Arquitetura Multi-Agente (Actor-Critic Loop)

O projeto é estruturado como um sistema de agentes autônomos que cooperam em um loop de feedback contínuo para otimizar e validar currículos:

1. **Harvey (Orquestrador/Contexto)**: Coleta dados do candidato, clona seus repositórios públicos e monta o ambiente isolado de sessão.
2. **Karen Guard (Avaliadora/Critic)**: Analisa o currículo do candidato contra a vaga de emprego e valida as alegações técnicas inspecionando o código real nos repositórios. É ultra-cética e gera um dossiê detalhado de inconsistências e defeitos (`evaluation.md`).
3. **Bob Revisor (Editor/Generator)**: Consome o currículo original, a vaga de emprego e o relatório de defeitos da Karen, reescrevendo o currículo para blindá-lo contra as críticas e ajustar a senioridade real do candidato.

---

## Glossário de Módulos

* [Harvey (Orchestrator)](file:///home/alex/git/my/meta_2028/harvey_guy/README.md) - Coleta de contexto e preparação do workspace.
* [Karen Guard (Evaluator)](file:///home/alex/git/my/meta_2028/karen_guard/Readme.md) - Validador estático cético e geração de relatório de fit técnico.
* [Bob Revisor (Editor)](file:///home/alex/git/my/meta_2028/bob_revisor/README.md) - Revisão e otimização automatizada do CV.

---

## Arquitetura de Sessão e Logs

A cada execução do orquestrador principal (`harvey_guy/main.py`), uma nova sessão com identificador único (UUID) é gerada.

### Diretório de Sessão
Uma pasta dedicada para a sessão atual é criada no diretório temporário do sistema:
`/tmp/karen_guard_<UUID>/`

### Localização dos Logs
O arquivo de log da execução atual fica armazenado diretamente dentro desta pasta de sessão:
`/tmp/karen_guard_<UUID>/karen_guard_core.log`

Os logs possuem timestamps detalhados e um contador sequencial de mensagens (`[count]`) para rastreamento preciso da execução do pipeline.
