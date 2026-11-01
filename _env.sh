# Variáveis comuns aos scripts (carregado via `source`).
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export OPENJARVIS_HOME="$RAIZ/dados"          # config, bancos, logs, cache
export OPENJARVIS_LANG="pt-BR"                 # CLI em português
export VIRTUAL_ENV="$RAIZ/venv"
export PATH="/Applications/Ollama.app/Contents/Resources:$RAIZ/venv/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
PORTA="${OPENJARVIS_PORT:-8000}"
