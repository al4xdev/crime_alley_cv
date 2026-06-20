# Briefing mestre — Projeto de CV e candidaturas automatizadas

> Este documento é o contexto central para o projeto de geração e adaptação de currículo.
> Deve ser indexado no MCP do Claude Code como fonte primária de identidade profissional.
> Combine com as retrospectivas pessoais para gerar CVs posicionados por vaga.

---

## 1. Identidade profissional real (vs. cargo na carteira)

| Dimensão | Realidade |
|---|---|
| Cargo na carteira | Analista/Desenvolvedor Pleno |
| Cargo operacional atual | Tech Leader (promovido há ~5 meses) |
| Nível de atuação real | **Staff Engineer / Tech Lead Sênior** |
| Alvo de candidatura | Tech Lead Sênior · Staff Engineer L5/L6 |
| Empresa atual | Accenture (1.5 anos) |
| Experiência anterior | ~1 ano como Desenvolvedor Freelancer (projetos próprios, automação, primeiros trabalhos com AI) |
| Tempo total na área | ~2.5 anos (freelancer + Accenture) |

**Argumento central do CV:**
O candidato opera como Staff Engineer de fato — constrói a plataforma técnica que os times consomem, define arquitetura, mentora sêniores e plenos, e representa a frente técnica em reuniões com clientes e gestão. Entrou na Accenture já como Pleno (experiência freelancer explica a senioridade de entrada), e foi promovido a Tech Lead em ritmo acelerado. O cargo na carteira é consequência de progressão rápida, não reflexo do nível real de atuação.

---

## 2. Stack técnica principal

### Core
- **Python** — foco em GenAI, backend, automação
- **Databricks** — especialista em dados + GenAI no ambiente de produção
- **Pydantic** — uso avançado como schema de validação server-side, inclusive para processamento de imagens e GenAI pipelines

### Infraestrutura e DevOps
- **Docker** — containerização de serviços (ex: API de TV/wake empacotada pra Home Assistant)
- **Azure DevOps** — pipelines CI/CD, gestão de issues, integração com Claude Code
- **Cloud orchestration** — orquestrador de cloud functions próprio

### AI / GenAI
- **Claude (Anthropic)** — integração via API e MCP, uso avançado com Claude Code
- **Gemini** — customização para comportamento similar ao Claude
- **LLM via MCP** — integração em projetos próprios (card game simulator)
- **GenAI frameworks** próprias — processamento de texto aninhado, imagens, validação via Pydantic

### Sistemas e fundamentos
- **Linux** — uso desde criança, dotfiles altamente organizados, scripts próprios
- **TypeScript/Node** — projetos frontend e backend
- **Engenharia de Materiais** (formação) — raciocínio de sistemas, modelagem, rigor analítico

---

## 3. Escopo atual na Accenture

### Contexto do projeto
- Projeto de GenAI enterprise com **dois grandes clientes telecom do Brasil**
- Time dividido em duas frentes, cada uma com: 2 devs (sêniores/plenos) + 1 analista funcional
- Arquiteto principal: profissional com 15 anos de Meta — atua na camada de decisão estratégica

### Papel real do candidato
1. **Engenheiro principal de plataforma** — cria e mantém as frameworks usadas por todos os devs no Databricks
2. **Tech Lead das duas frentes** — decisões técnicas, code review via pipeline automatizado, direcionamento de devs
3. **Mentor** — mentora sêniores e plenos que estão abaixo dele formalmente mas acima na carteira
4. **Representante técnico** — vai em reuniões técnicas com clientes e gestão em dupla com o arquiteto; defende decisões de arquitetura que o arquiteto apresenta
5. **Engenheiro de produtividade** — criou pipeline com Claude Code rodando validações automáticas, gerando issues e revisores de PR com tasks diretos no DevOps

### Dinâmica de trabalho
- Times focam em funcional; candidato foca em manter a plataforma, performance e segurança
- Foco com os devs é precisão de resultado — não gestão de pessoas
- Atua solo nas frentes de frameworks e infraestrutura de desenvolvimento

---

## 4. Histórico de experiência (linha do tempo do CV)

### Freelancer — Desenvolvedor (~ 1 ano, antes da Accenture)
- Projetos próprios de automação, desenvolvimento web e primeiros experimentos com AI
- Explica a senioridade de entrada na Accenture como Pleno
- Não detalhar clientes específicos — posicionar como período de especialização autônoma

### Accenture — período pré-Tech Lead
- **Coordenador interino** em algum momento antes da promoção formal
  - Liderou ~8 pessoas em 3 projetos simultâneos (às vezes 4, atuando solo como Sênior em um)
  - Dois times dentro da divisão de GenAI da Accenture
  - Times de 2–3 devs cada
- Entrou como Pleno — **não mencionar Jr em nenhum momento no CV**

---

## 5. Projetos pessoais (portfólio GitHub)

Todos os projetos abaixo devem ser referenciados no CV como evidência de capacidade técnica autônoma.

| Projeto | Descrição técnica | Relevância pro CV |
|---|---|---|
| **Card game simulator** | Front + back rodando local ou via LLM por MCP | Arquitetura full-stack + integração LLM/MCP |
| **Crysis mods collection** | Coleção de mods próprios | Engenharia reversa, sistemas de baixo nível |
| **TV/wake API** | API simples para controlar TV, logs e wake-on-LAN, empacotada em Docker, integrada ao Home Assistant | Backend + Docker + IoT |
| **Dotfiles** | Scripts, configs, projetos globais do Claude Code e Gemini — os mais organizados de todos | Rigor técnico, automação, tooling |
| **Claude Code global projects** | Projetos de automação pessoal com Claude Code | AI engineering, MCP, produtividade |
| **Gemini custom config** | Configuração para aproximar Gemini do comportamento do Claude | Prompt engineering avançado, LLM tuning |

---

## 6. Frameworks a extrair da Accenture (futuros projetos OSS)

> Nota: extrair apenas a lógica e arquitetura próprias — sem código proprietário de cliente.

| Framework | Descrição | Stack |
|---|---|---|
| **GenAI text framework** | Processamento de GenAI com Pydantic, estruturas aninhadas, validação server-side via JSON | Python, Pydantic |
| **GenAI image framework** | Versão da framework acima para imagens, Pydantic como schema de preenchimento | Python, Pydantic, GenAI |
| **Cloud orchestrator** | Orquestrador de cloud functions próprio | Cloud, Python |
| **Outras libs internas** | Várias bibliotecas criadas ao longo dos projetos | Python |

---

## 7. Diferencial competitivo — o que poucos candidatos têm

Use estes pontos como argumentos em carta de apresentação, LinkedIn e entrevistas:

1. **Formação em Engenharia de Materiais** — raciocínio analítico e de sistemas que a maioria de dev autodidato não tem. Modelagem de problemas complexos é natural.

2. **Linux desde criança** — não é dev que aprendeu Linux no bootcamp. É alguém que cresceu entendendo o sistema operacional de baixo para cima.

3. **Visão de mercado crítica** — tem clareza de onde o mercado é imaturo e onde há valor real. Isso é raro e valioso em Staff Engineers que precisam influenciar direção técnica.

4. **AI-native de verdade** — não usa AI como copilot de autocomplete. Criou pipeline de CI com Claude Code, projetos com MCP, frameworks GenAI em produção. Opera como engenheiro da era de AI.

5. **Progressão desproporcional** — Tech Lead em 1.5 anos, mentorando sêniores, defendendo arquitetura ao lado de alguém com 15 anos de Meta. O mercado paga bem por esse perfil quando bem apresentado.

---

## 8. Como esse engenheiro pensa — contexto para geração de narrativa

> Esta seção calibra o tom e a voz do CV e da carta de apresentação.
> Não é para ser citada diretamente — é para o modelo entender quem está por trás do texto.

### Modelo mental

Não pensa em linha reta. Pensa em rede — variáveis, contextos, consequências de segunda ordem. Exemplos que emergem naturalmente no trabalho:

- Dificuldade não é sinônimo de tempo — é composição de taxa de erro, duração de exposição e volume de repetição
- Preço não é custo — soma agilidade, confiabilidade e risco no valor real de uma decisão
- Comportamento humano vem de contexto, não de caráter — corrige o Erro Fundamental de Atribuição naturalmente, sem ter aprendido o nome

### Estilo de liderança

**Liderança Servidora com Arquitetura de Ambiente** — chegou a esses conceitos sozinho, por observação.

Na prática:
- Não centraliza, distribui com risco calculado — manda o dev pra reunião com cliente quando confia nele
- Não cobra relatório — cria barreiras técnicas que geram visibilidade naturalmente (ex: bloquear Databricks para forçar sincronização com workspace)
- Usa linters e ferramentas como correção sistêmica — o sistema corrige, não o líder
- Desenvolve as pessoas até não precisarem dele para tarefas rotineiras
- Prefere ser a influência técnica por baixo do cargo formal — move direções sem precisar do discurso

### Como aprende

- Entra em qualquer área sem ego de iniciante
- Processo invariável: mapeia o sistema, itera, ajusta pela taxa de erro
- Intuição precede a explicação — chega em conclusões avançadas antes de ter linguagem formal pra elas

### O que isso significa para o CV e a carta

- Não deve soar como lista de tarefas — deve soar como alguém que pensa em sistemas e resolve problemas estruturalmente
- Bullet points de impacto devem refletir decisões, não execuções
- A narrativa de progressão acelerada é legítima: o título chegou como consequência, não como objetivo
- Não super-dimensionar nem sub-dimensionar — o candidato ainda está aprendendo a aplicar a si mesmo a mesma visão sistêmica que aplica a tudo

---

## 9. Validação externa do GitHub (análise por agente RH isolado)

> Resultado de avaliação técnica real feita por agente simulado sem contexto prévio do candidato.
> Projetos analisados: `sunshine-mobile-streaming-orchestrator`, `crysis-remastered-mods`, `dotfiles`, `lg-webos-wol-api`

**Diagnóstico do agente:**

- **Mentalidade shift-left** — modela cenários de falha antes de construir, não depois
- **Sem over-engineering** — utilitários objetivos, código limpo, sem dependências supérfluas
- **Testes unitários de shell em dotfiles** — classificado como "raríssimo" para projetos pessoais
- **Desenho programático de assets** nos mods de Crysis via .NET/PowerShell — em vez de ferramenta gráfica manual
- **Interop de baixo nível** com WinRT API via PowerShell no orchestrator de streaming
- **Pronto para produção** na TV API — Dockerfile otimizado, .env.example, tratamento de exceções resiliente

**Veredito:** *"Maturidade de Engenharia de Software Sênior. Competência técnica justifica liderança técnica. Apto."*

**Como usar no CV:** Esses pontos sustentam a seção de projetos pessoais, especialmente para vagas que pedem ownership e engineering excellence. O agente chegou à mesma conclusão de um recrutador real — sem saber quem era o candidato.

---

## 10. Validação cruzada — perfil comportamental vs. código real

> Segunda rodada de validação: o perfil comportamental (gerado por LLM a partir de conversa espontânea) foi submetido a um agente recrutador independente, que o correlacionou com os repositórios públicos sem saber que era o mesmo candidato. Resultado: correlação 1:1 entre o que o candidato declara e o que o código prova.

| O que o perfil diz | O que o código prova |
|---|---|
| "Cria barreiras técnicas em vez de cobrar relatório" | `test_dotfiles.fish` — suíte de testes unitários que valida scripts locais automaticamente antes de rodar |
| "Pensa em rede, consequências de segunda ordem" | `setup.ps1` — remove chaves antigas de agendamento, varre registros do Winget, apaga drivers virtuais duplicados antes de subir o serviço |
| "Orquestra sistemas complexos" | `orchestrator.ps1` — integra WinRT API, serviços Windows, XML dinâmico de drivers e comandos de projeção do SO em um único fluxo |
| "Masterizou mod de Crysis" | `Pack-Mods.ps1` e `pack_mods.py` — pipeline de build com normalização de caminhos para as idiossincrasias da CryEngine |

**Veredito do agente:** *"A maturidade de engenharia equivale à de profissionais com 6 a 8 anos de mercado. Vale a pena chamar o time técnico — a chance de reprovação em sabatina técnica é extremamente baixa."*

**Perguntas sugeridas pelo agente para validação rápida:**
- "No projeto de streaming, como você resolveu o problema de concorrência e instâncias duplicadas do driver de vídeo virtual via script?"
- "Por que você criou testes unitários para sua própria configuração de shell, e qual o ganho prático?"

**Validação cruzada significa:** dois agentes independentes, sem saber que avaliavam a mesma pessoa, chegaram à mesma conclusão. Um analisou código. O outro analisou perfil comportamental. Os resultados se sobrepõem ponto a ponto. Isso não é coincidência — é consistência.

---

## 🔖 Lema de candidatura

> **"Se houver dúvida sobre meu nível, traga o time técnico. Estou disposto a abrir qualquer projeto, explicar qualquer decisão e ser validado por quem entende."**

Este lema deve ser a postura em toda entrevista onde o tempo de experiência formal for questionado. Não é defensivo — é confiante. A validação não depende de tempo de carteira. Depende de evidência técnica, e a evidência está disponível e pública.

---

## 11. Instruções para o projeto de CV no Claude Code

### Estrutura sugerida do projeto

```
cv-engine/
├── context/
│   ├── briefing.md              ← este documento
│   ├── retrospectivas/          ← arquivos de retrospectiva pessoal
│   └── projetos.md              ← detalhamento dos projetos
├── templates/
│   ├── cv_base.md               ← CV base em markdown
│   ├── cv_base.json             ← versão estruturada para manipulação
│   └── cover_letter_base.md     ← carta base
├── vagas/
│   └── [empresa]/
│       ├── jd.md                ← job description copiada
│       ├── cv_adaptado.md       ← CV gerado para essa vaga
│       └── cover_letter.md      ← carta gerada
├── scripts/
│   ├── adapt_cv.py              ← recebe JD, gera CV adaptado via API
│   ├── generate_cover.py        ← gera carta de apresentação
│   └── batch_apply.py           ← automação de candidaturas
└── mcp/
    └── cv_context_server.py     ← servidor MCP que expõe o contexto pro Claude Code
```

### Prompt base para adaptação de CV

Quando o script `adapt_cv.py` chamar a API, usar este system prompt:

```
Você é um especialista em recrutamento técnico para posições de Staff Engineer e Tech Lead Sênior.

Você tem acesso ao perfil completo do candidato (briefing + retrospectivas).
Sua tarefa é adaptar o CV base para a vaga fornecida, maximizando o fit técnico e de linguagem.

Regras:
1. Nunca inventar experiências — apenas reframing do que existe
2. Priorizar bullet points com impacto mensurável (%, escala, times)
3. Espelhar a linguagem da JD (termos técnicos, stack, metodologia)
4. Posicionar o candidato sempre como Staff/Tech Lead Sênior — nunca como pleno
5. Destacar o pipeline CI com Claude Code e as frameworks GenAI como diferenciais
6. Manter o CV em no máximo 2 páginas
7. Output em markdown estruturado pronto para conversão em PDF
```

### Campos obrigatórios em cada CV gerado

- **Headline:** Tech Lead / Staff Engineer · GenAI · Python · Databricks
- **Summary:** 3–4 linhas posicionando como engenheiro de plataforma AI-native
- **Experiência Accenture:** separar em Tech Lead (atual) e período como Pleno/Coordenador interino
- **Freelancer:** primeiro item da experiência — posicionado como especialização autônoma pré-Accenture
- **Projetos pessoais:** seção própria linkando GitHub
- **Stack:** agrupada por categoria (AI/GenAI, Backend, Infra, Dados)

---

## 12. Alvos de candidatura

### Brasil (remoto)
- Nubank, iFood, Mercado Livre, PicPay, Itaú Tech, Bradesco Tech
- Startups de AI série A/B com eng forte: Intelia, Cortex, Nuvem Fiscal, etc.
- Consultorias premium: ThoughtWorks, MAAS, CI&T (nível acima do atual)

### Exterior (remoto, USD/EUR)
- Empresas com times distribuídos: Deel, Remote, Cloudflare, Elastic
- Startups de AI com eng distribuída — buscar no LinkedIn com filtro "remote" + "staff engineer" + "python"
- Foco em empresas que já têm brasileiros no time (facilita processo)

### Faixas salariais esperadas (referência Jun/2025)
| Nível | Brasil (remoto) | Exterior (remoto) |
|---|---|---|
| Tech Lead Sênior | R$ 18k–28k/mês | USD 80k–120k/ano |
| Staff Engineer | R$ 25k–40k/mês | USD 120k–180k/ano |

---

## 13. Checklist antes de cada candidatura

- [ ] CV adaptado com linguagem espelhada da JD
- [ ] LinkedIn atualizado com cargo "Tech Lead | Staff Engineer · GenAI"
- [ ] GitHub com pelo menos card game + dotfiles + TV API documentados
- [ ] Carta de apresentação com o argumento "venho de trajetória autônoma + promovido a Tech Lead em 1.5 anos na Accenture"
- [ ] Preparar 3 histórias STAR: maior problema técnico resolvido, decisão de arquitetura defendida, impacto de negócio mensurável

---

*Documento gerado em Jun/2025 — atualizar com retrospectivas pessoais antes de rodar o script de adaptação.*
