# Backlog — Actor-Critic CV Optimization Loop

O core (loop Actor-Critic + Vera/Donna) está estável e os itens planejados originais foram entregues e integrados ao container global.

> Princípio de design (decidido em sessão): migrar pro determinístico **apenas o que
> falha em silêncio**. O que falha alto, o agente cura sozinho — deixa na prosa.

---

## 🚀 Próximos Passos (A Fazer)

### TASK-02: Otimização de Consumo de Tokens Globais
- **Ignore Global (ex: `.agentignore`)**: Criar um mecanismo de ignore que filtre arquivos desnecessários (como `.lock`, arquivos de configuração de ferramentas, imagens, binários e dependências pesadas) para que **nenhum** agente (não apenas a Karen, mas todos os agentes do pipeline) consuma tokens lendo arquivos irrelevantes durante o processo.
- **Estratégias de Economia Global**: Pesquisar e planejar formas de otimização adicionais, como o uso de *Gemini Context Caching* para dados estáticos compartilhados (como os repositórios clonados e vaga) e telemetria básica para medir o consumo de tokens por iteração.

### TASK-08: Remoção de Dependência de Wayland & Ativação do atd no Docker
- **Remover Wayland**: Remover os requisitos e verificações de Wayland (`wl-copy` / `wl-clipboard`) do pipeline e dos runbooks/documentos de requisitos, já que o container executa em modo headless.
- **Ativação Automática do `atd`**: Configurar a inicialização automática do daemon `atd` no container (seja no script de entrada ou no fluxo de execução), evitando a necessidade de inicialização manual via terminal.

### TASK-09: Correção de Pulo de Perguntas pós-retorno do Pager agy
- **Problema**: Ao sair do visualizador interativo (pager) do `agy` pressionando `esc` para retornar ao fluxo principal do agente orquestrador, as perguntas interativas do terminal foram puladas/ignoradas e o agente não conseguiu responder adequadamente.
- **Solução**: Investigar e depurar a captura de stdin/fluxo interativo quando o `agy` suspende/retorna ou quando há subprocessos interativos, garantindo que o canal de entrada padrão do terminal (stdin) e o fluxo do orquestrador não sejam corrompidos ao fechar o pager.

### TASK-10: Restrições de Prompt e Rede da Karen Guard
- **Problema**: A Karen tenta clonar repositórios via internet (`git clone`) e faz buscas gerais no filesystem root (`/`), gerando timeouts e consumo excessivo de contexto/tokens.
- **Solução**: Adicionar uma instrução clara no prompt de persona da Karen (`karen_guard/prompt_persona.txt`) explicitando que ela não tem acesso à internet (e que não deve tentar executar comandos git remotos), devendo basear sua auditoria estritamente nos arquivos locais pré-clonados pelo Shadow em `/app/session/repos/`, limitando suas buscas de arquivos apenas aos diretórios da sessão.
