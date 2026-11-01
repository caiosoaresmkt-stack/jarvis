#!/usr/bin/env bash
# Instala o OpenJarvis (PT-BR) nesta pasta. Rode como usuário comum (não root).
#   ./instalar.sh [--sem-modelo] [--modelo qwen3.5:4b] [--sem-rust]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
MODELO="qwen3.5:2b"; BAIXAR=1; RUST=1
while [[ $# -gt 0 ]]; do case "$1" in
  --sem-modelo) BAIXAR=0 ;; --sem-rust) RUST=0 ;;
  --modelo) MODELO="$2"; shift ;;
  *) echo "opção desconhecida: $1" >&2; exit 2 ;; esac; shift; done

if [[ "$(id -u)" -eq 0 ]]; then echo "Não rode como root; use seu usuário normal." >&2; exit 1; fi
for t in git curl python3; do command -v $t >/dev/null || { echo "Instale '$t' primeiro." >&2; exit 1; }; done

mkdir -p "$OPENJARVIS_HOME"
echo "[1/6] uv"; export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh || python3 -m pip install --user uv
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "[2/6] Ambiente Python"
[[ -x "$RAIZ/venv/bin/python" ]] || uv venv --python 3.13 "$RAIZ/venv" || uv venv --python 3.12 "$RAIZ/venv"
uv pip install --python "$RAIZ/venv/bin/python" -e "$RAIZ/app[server]"

echo "[3/6] Interface web (já vem compilada; recompila só se faltar)"
if [[ ! -f "$RAIZ/app/src/openjarvis/server/static/index.html" ]]; then
  command -v npm >/dev/null || { echo "Node 22+/npm necessário para compilar a interface." >&2; exit 1; }
  (cd "$RAIZ/app/frontend" && npm ci --no-audit --no-fund && npx vite build)
fi

echo "[4/6] Ollama (motor de modelos locais)"
if ! command -v ollama >/dev/null; then
  echo "    Ollama não encontrado. Instalando (pede sudo): https://ollama.com/install.sh"
  curl -fsSL https://ollama.com/install.sh | sh || echo "    Falhou — instale manualmente em https://ollama.com e rode de novo."
fi
if command -v ollama >/dev/null && ! pgrep -f "ollama serve" >/dev/null; then
  nohup ollama serve >"$RAIZ/dados/ollama.log" 2>&1 & sleep 3
fi
mkdir -p "$OPENJARVIS_HOME"
if [[ $BAIXAR -eq 1 ]] && command -v ollama >/dev/null; then echo "    Baixando modelo $MODELO"; ollama pull "$MODELO" || true; fi

echo "[5/6] Configuração (análises/telemetria DESLIGADAS)"
[[ -f "$OPENJARVIS_HOME/config.toml" ]] || jarvis init --engine ollama --no-analytics --no-download --no-scan --force >/dev/null
jarvis config set intelligence.default_model "$MODELO" >/dev/null 2>&1 || true

if [[ $RUST -eq 1 ]]; then
  echo "[6/6] Extensão Rust (memória/segurança) — pode levar alguns minutos"
  if command -v cargo >/dev/null; then
    (cd "$RAIZ/app" && uv pip install --python "$RAIZ/venv/bin/python" maturin >/dev/null && \
      maturin develop --release -m rust/crates/openjarvis-python/Cargo.toml) || echo "    Rust falhou; o app funciona sem ele (sem memória persistente)."
  else echo "    cargo não encontrado (https://rustup.rs). Pulando; o chat funciona sem a extensão."; fi
fi
echo; echo "Pronto! Rode:  ./iniciar.sh"
