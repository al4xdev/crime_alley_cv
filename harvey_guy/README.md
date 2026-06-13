# Harvey (Orchestrator)

Módulo responsável pela orquestração inicial do pipeline, ingestão de dados locais e coleta de contexto do candidato.

## Funcionalidades

1. **Gestão de Sessão**: Cria o diretório de execução temporário `/tmp/karen_guard_<UUID>/` e inicia os logs detalhados do pipeline.
2. **Ingestão de Documentos**: Copia os arquivos locais de currículo, briefing e vaga de `data/docs/` para a pasta de sessão.
3. **Mapeamento de Repositórios**: Detecta o nome do usuário no GitHub através do repositório local e consulta a API do GitHub para obter a lista de repositórios públicos.
4. **Clonagem e Workspace**: Efetua a clonagem assíncrona dos repositórios públicos na pasta `/tmp/karen_guard_<UUID>/repos/` para posterior análise de código.
5. **Output de Sessão**: Imprime o ID da sessão ao final para encadeamento de scripts de shell.

## Execução

O entrypoint principal do Harvey pode ser executado diretamente pelo Python:

```bash
uv run python harvey_guy/main.py
```
