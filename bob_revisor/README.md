# Bob Revisor (Editor)

Módulo responsável pela revisão crítica e otimização automatizada do currículo do candidato baseando-se no relatório de defeitos gerado pelo avaliador.

## Papel no Loop Multi-Agente (Generator)

Enquanto a Karen atua como o validador rigoroso (Critic) que destrói o currículo apontando pontas soltas e inconsistências, o **Bob Revisor** atua como o editor inteligente (Generator):

1. **Leitura de Insumos**: Ingere o currículo original (`cv.md`), os requisitos da vaga (`job.md`) e as inconsistências e alertas mapeados no relatório da Karen (`evaluation.md`).
2. **Correção de Defeitos**: Reescreve seções do currículo para mitigar as críticas da Karen (ex: sugerir adequações em termos inflados, detalhar melhor as rotinas de otimização aplicadas).
3. **Alinhamento de Stack**: Ajusta o foco do currículo para evidenciar as tecnologias reais encontradas nos repositórios, garantindo que o currículo seja extremamente competitivo, mas 100% verídico.
4. **Blindagem**: Produz um novo currículo otimizado para que passe nas triagens automatizadas e humanas com notas de fit técnico mais elevadas.

## Estrutura Planejada

```
bob_revisor/
├── README.md
├── Dockerfile               ← Ambiente isolado para revisão
├── run.sh                   ← Inicia o processo de revisão do CV
└── prompt_revisor.txt       ← Instruções da persona de editor técnico do Bob
```
