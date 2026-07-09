# Erro de Execução: Prompt Interativo de Confiança de Pasta (Hanging)

## 🔍 Descrição do Problema
Durante a execução do setup da Karen Guard no container Podman/Docker, o processo trava indefinidamente no seguinte prompt de interação:

```
Welcome to the Antigravity CLI. You are currently not signed in.
Do you trust the contents of this project?
Antigravity CLI requires permission to read, edit, and execute files here.

> Yes, I trust this folder
  No, exit
```

## 🕵️ Causa Raiz
1. O script `karen_guard/run.sh` executa um teste de autenticação com `agy models >/dev/null 2>&1`.
2. Se este comando falhar por qualquer motivo (ex: warnings do podman gravados em stderr sendo falhas de saída ou oscilação de rede), o script inicia o fluxo de login interativo com `agy`.
3. O `agy` inicia no diretório `/app` do container e verifica se `/app` está listado em `trustedWorkspaces` no `settings.json`.
4. No arquivo `settings.json` copiado do host, apenas caminhos locais como `/home/alex/git/my/meta_2028` estão marcados como confiáveis. O caminho `/app` (que só existe dentro do container) não está na lista, forçando o prompt interativo a aguardar entrada de teclado indefinidamente no loop de background.

## 🛠️ Solução Proposta
No arquivo `karen_guard/run.sh`, podemos injetar o caminho `/app` na lista de workspaces confiáveis do arquivo `settings.json` temporário antes de invocar o container, ou garantir confiança automática.
