# Karen Guard — Backlog

> Funcionalidades planejadas para o ambiente de avaliação isolado.
> Este arquivo é o planejamento específico do módulo Karen Guard.

---

## Próximas entregas

### 3. evaluator.py — Avaliador Estateless
- [ ] Desenvolver script de avaliação baseado no SDK do Gemini/Claude.
- [ ] Carregar a persona do recrutador sênior a partir de um arquivo de prompt.
- [ ] Ler o CV e arquivos do repositório a partir do volume montado.
- [ ] Retornar o relatório estruturado de avaliação (`evaluation.md`).

---

## Fora de escopo (Simplificado)

- **Anonimização de CV**: Removida. A avaliação será feita com o CV direto, pois a sessão limpa da API já garante o isolamento contra dados históricos.
- **Mapeamento de credenciais locais (gcloud config mount)**: Não será feito a menos que seja estritamente necessário. Usaremos variáveis de ambiente padrão (`GEMINI_API_KEY`) para autenticação stateless da API.
