# Job-Stack & Karen Guard

Orquestrador e avaliador de candidaturas automatizadas.

## Arquitetura de Sessão e Logs

A cada execução do orquestrador principal (`harvey/main.py`), uma nova sessão com identificador único (UUID) é gerada.

### Diretório de Sessão
Uma pasta dedicada para a sessão atual é criada no diretório temporário do sistema:
`/tmp/karen_guard_<UUID>/`

### Localização dos Logs
O arquivo de log da execução atual fica armazenado diretamente dentro desta pasta de sessão:
`/tmp/karen_guard_<UUID>/karen_guard_core.log`

Os logs possuem timestamps detalhados e um contador sequencial de mensagens (`[count]`) para rastreamento preciso da execução do pipeline.
