novos agentes:

1. vera_guy/ — agente de roleplay que conduz uma conversa 
estruturada com o usuário para popular data/docs/who_are_u.md. 
Deve fazer perguntas abertas sobre carreira, forma de pensar, 
liderança e valores. Salva o arquivo ao final.

2. donna_guy/ — agente coach que lê o evaluation.md gerado pela 
Karen e produz um plano de ação em data/docs/action_plan.md com: 
gaps técnicos a fechar, tópicos para revisar antes de entrevistas, 
e projetos públicos a criar ou melhorar para subir o score, ele roda ao final de tudo.

3. harvey_shadow/ — atulziar subagente do harvey para conseguir fazer pesquisa de empresa na internet ele recebe o 
nome da empresa da vaga e popula 
fmp/karen_guard_$SESSION_ID/company_info.md com: tamanho, stack 
tecnológica, cultura, vagas abertas recentes e notícias relevantes. 
Este agente é chamado pelo Harvey no Step 1 em paralelo com a 
clonagem de repositórios.