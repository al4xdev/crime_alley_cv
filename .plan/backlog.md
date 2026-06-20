# Backlog — Actor-Critic CV Optimization Loop

O core (loop Actor-Critic + Vera/Donna) está estável e os itens planejados originais foram entregues e integrados ao container global.

> Princípio de design (decidido em sessão): migrar pro determinístico **apenas o que
> falha em silêncio**. O que falha alto, o agente cura sozinho — deixa na prosa.

---

## 🚀 Próximos Passos (A Fazer)

### TASK-02: Otimização de Consumo de Tokens Globais
- **Ignore Global (ex: `.agentignore`)**: Criar um mecanismo de ignore que filtre arquivos desnecessários (como `.lock`, arquivos de configuração de ferramentas, imagens, binários e dependências pesadas) para que **nenhum** agente (não apenas a Karen, mas todos os agentes do pipeline) consuma tokens lendo arquivos irrelevantes durante o processo.
- **Estratégias de Economia Global**: Pesquisar e planejar formas de otimização adicionais, como o uso de *Gemini Context Caching* para dados estáticos compartilhados (como os repositórios clonados e vaga) e telemetria básica para medir o consumo de tokens por iteração.

### TASK-11: Persistência de Camadas e Cache do Podman (Volume Mount)
- **Problema**: O build do sandbox `karen_guard` ocorre dentro do container orquestrador e leva de 4 a 6 minutos em cada execução inicial do pipeline, pois a pasta de storage do Podman (`/var/lib/containers`) é efêmera e reinicia limpa a cada `docker run` do container global.
- **Solução**: Modificar o script [start.sh](file:///home/alex/git/my/crime_alley_cv/start.sh) para montar um volume Docker nomeado persistente (ex: `-v crime_alley_podman_storage:/var/lib/containers`) no container global, fazendo com que as camadas de build do Podman persistam no host entre execuções do container global.
