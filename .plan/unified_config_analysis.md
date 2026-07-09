# Análise de Unificação de Configurações (.plan)

Analisamos a estrutura do projeto buscando outros pontos de configuração que podem ser centralizados no diretório `/config` do projeto sem comprometer a separação de responsabilidades e o isolamento dos agentes.

---

## 🔍 Candidatos Detectados

### 1. Personas e Prompts dos Agentes
* **Caminho Atual**: `karen_guard/prompt_persona.txt` (e potencialmente outros prompts em `harvey_guy/shadow.md`).
* **Sugestão**: Criar um subdiretório `config/prompts/` (ex: `config/prompts/karen/persona.txt`).
* **Prós**: Reúne em um único lugar a definição comportamental de todos os agentes que compõem o sistema. Facilita o ajuste fino de comportamento em lote.
* **Contras**: Prompts de personas costumam ser muito acoplados à lógica do agente que os executa. Afastá-los do diretório do agente pode prejudicar o contexto local de desenvolvimento.

### 2. Scripts de Validação de Limites (Boundaries)
* **Caminho Atual**: Pasta `boundaries/` na raiz do projeto (contém vários scripts `.fish` de checagem pre/post).
* **Sugestão**: Mover a pasta para `config/boundaries/`.
* **Prós**: Limpa a raiz do repositório e centraliza as políticas de contorno/fronteiras como parte das "configurações de segurança do projeto".
* **Contras**: Nenhum impacto negativo relevante de isolamento, apenas necessidade de ajustar os caminhos de chamada nos scripts orquestradores (como `harvey_guy`).

### 3. Dockerfiles e Arquivos de Dependência
* **Caminho Atual**: `karen_guard/Dockerfile`, `karen_guard/requirements.txt` (e `Dockerfile` na raiz).
* **Sugestão**: **Manter como estão.**
* **Justificativa**: Cada agente ou serviço (como `karen_guard`) precisa de total isolamento em seu ambiente de execução. Agrupar os `Dockerfiles` em um local centralizado dificultaria o contexto de build do container (`podman build`), uma vez que o Docker/Podman necessita copiar os arquivos locais do agente para dentro da imagem de forma isolada.

---

## 💡 Recomendação
Como o objetivo é **não sobrecarregar o código nem quebrar o isolamento atual**, a recomendação é:

1. **Prioridade Média**: Mover os scripts de `boundaries/` para `config/boundaries/`, pois eles representam políticas de segurança centralizadas do projeto.
2. **Prioridade Baixa**: Centralizar os prompts em `config/prompts/` apenas se houver necessidade frequente de alterar o comportamento dos agentes em conjunto. Caso contrário, mantê-los nos respectivos diretórios de agentes para preservar o acoplamento lógico saudável.
