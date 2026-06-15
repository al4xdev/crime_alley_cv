Crie três novos subagentes no projeto, cada um com seu próprio 
diretório e main.md:

1. vera_guy/ — agente de roleplay que conduz uma conversa 
estruturada com o usuário para popular data/docs/quem_sou.md. 
Deve fazer perguntas abertas sobre carreira, forma de pensar, 
liderança e valores. Salva o arquivo ao final.

2. donna_guy/ — agente coach que lê o evaluation.md gerado pela 
Karen e produz um plano de ação em data/docs/action_plan.md com: 
gaps técnicos a fechar, tópicos para revisar antes de entrevistas, 
e projetos públicos a criar ou melhorar para subir o score.

3. harvey_shadow/ — agente de pesquisa de empresa que recebe o 
nome da empresa da vaga e popula 
/tmp/karen_guard_$SESSION_ID/company_info.md com: tamanho, stack 
tecnológica, cultura, vagas abertas recentes e notícias relevantes. 
Este agente é chamado pelo Harvey no Step 1 em paralelo com a 
clonagem de repositórios.

Cada agente deve ter seu main.md seguindo o mesmo padrão do 
billf/main.md — com seção de inputs, regras de isolamento e 
plano de execução passo a passo.
