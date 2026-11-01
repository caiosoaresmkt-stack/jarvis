# OpenJarvis — versão PT-BR

IA pessoal que roda **localmente** (upstream: https://github.com/open-jarvis/OpenJarvis, Apache-2.0).
Esta pasta contém o código, a interface web já compilada e a localização em português do Brasil.

## Uso rápido

```bash
./instalar.sh        # 1ª vez: Python/venv, dependências, Ollama, modelo e extensão Rust
./iniciar.sh         # sobe o servidor e abre http://127.0.0.1:8000
./parar.sh           # encerra
./bin/jarvis ask "Olá!"      # CLI (usa os dados desta pasta)
./bin/jarvis doctor          # diagnóstico
```

Opções do instalador: `--sem-modelo`, `--modelo qwen3.5:4b`, `--sem-rust`.
Tudo (config, bancos, logs) fica em `dados/`; nada é gravado em `~/.openjarvis`.
Análises/telemetria vêm **desligadas** (`dados/config.toml`).

## O que foi feito neste fork

| Área | Mudança |
|---|---|
| Interface web | Camada de i18n em tempo de execução (`app/frontend/src/i18n/`): ~1.000 textos traduzidos (dicionário `pt-BR.json`), cobrindo telas, placeholders, tooltips, toasts e mensagens de erro. Texto digitado/gerado pelo usuário e pelo modelo **não** é alterado. |
| Painel de economia | `server/dashboard.py` traduzido. |
| Modelo | Prompt de sistema padrão em PT-BR (`core/config.py`): responde em português do Brasil salvo pedido contrário. |
| CLI | `cli/_ptbr.py`: ajuda do Click ("Uso/Opções/Comandos", erros) e descrição dos comandos; `jarvis doctor` totalmente em português. |
| Scripts | `instalar.sh`, `iniciar.sh`, `parar.sh`, `bin/jarvis` (a instalação upstream recusa rodar como root e grava em `~/.openjarvis`). |
| Testes | Novo teste do i18n; testes do CLI fixam `OPENJARVIS_LANG=en`. |

Voltar ao inglês: interface → `http://127.0.0.1:8000/?lang=en`; CLI → `OPENJARVIS_LANG=en`.

## Limitações conhecidas (leia)

* **CLI**: só o nível raiz e o `doctor` estão em PT-BR. `--help` e mensagens de subcomandos (`ask`, `serve`, `init`…) seguem em inglês (~180 mil linhas de Python sem i18n).
* **Interface**: a tradução é por correspondência exata de texto. Textos novos do upstream aparecem em inglês até serem adicionados em `app/tools/i18n/` (ver abaixo). Textos vindos do backend (ex.: mensagens de erro da API) ficam em inglês.
* **Qualidade do português depende do modelo**: `qwen3.5:2b` (padrão) é pequeno; prefira `qwen3.5:4b`+ se tiver RAM.
* Primeira abertura mostra um convite de "ranking/sorteio" (envia nome/e-mail a um serviço externo se aceito). Use **"Continuar sem compartilhar"**.

## Manutenção das traduções

```bash
node app/tools/i18n/extract_strings.mjs app/frontend/src app/tools/i18n/strings.en.json   # extrai textos
# edite app/tools/i18n/pt*.tsv (índice<TAB>tradução) ou app/tools/i18n/extras.json (inglês→PT)
python3 app/tools/i18n/build_dict.py                                                       # gera pt-BR.json
(cd app/frontend && npx vite build)                                                        # recompila a interface
```
Placeholders: `{}` = valor dinâmico; `{1}`, `{2}`… permitem reordenar/repetir.
