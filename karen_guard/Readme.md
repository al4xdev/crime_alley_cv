# Karen Guard

Avaliador isolado de candidatos. Simula um recrutador técnico sênior que nunca viu o candidato antes.

O candidato vira **Alexa** antes de qualquer avaliação. O agente não sabe quem você é. Ele só vê o código e o CV.

---

## Como rodar

### Via Docker (recomendado — isolamento total)

```bash
docker build -t karen_guard .

docker run --rm \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  karen_guard python main.py \
    --cv input/cv_base.md \
    --github input/github_summary.md \
    --output output/evaluation.md
```

### Via Python direto

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

python main.py \
  --cv cv_base.md \
  --github github_summary.md \
  --output evaluation.md
```

---

## Arquivos necessários

| Arquivo | O que colocar |
|---|---|
| `input/cv_base.md` | Seu CV em markdown |
| `input/github_summary.md` | Resumo manual do seu GitHub (use o template) |

**Antes de rodar:** edite o dicionário `REPLACEMENTS` em `anonymize_cv.py` com seu nome real, username e empresa. Eles serão substituídos por "Alexa" antes da avaliação.

---

## O que o agente entrega

1. Resumo neutro do candidato
2. 3 pontos fortes com evidência específica
3. Red flags e gaps
4. 5 perguntas que faria na entrevista técnica
5. Veredito: Strong Yes / Yes / No / Strong No + justificativa

---

## Roadmap

Ver `BACKLOG.md`.
