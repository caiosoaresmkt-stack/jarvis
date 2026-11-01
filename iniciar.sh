#!/usr/bin/env bash
# Inicia o servidor + interface web do OpenJarvis em http://127.0.0.1:8000
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
mkdir -p "$OPENJARVIS_HOME"
if curl -fs "http://127.0.0.1:$PORTA/health" >/dev/null 2>&1; then echo "Já está rodando em http://127.0.0.1:$PORTA"; exit 0; fi
if command -v ollama >/dev/null && ! pgrep -f "ollama serve" >/dev/null; then
  nohup ollama serve >"$OPENJARVIS_HOME/ollama.log" 2>&1 & sleep 2
fi
nohup jarvis serve --port "$PORTA" "$@" >"$OPENJARVIS_HOME/servidor.log" 2>&1 &
echo $! >"$OPENJARVIS_HOME/servidor.pid"
OK=0
for i in $(seq 1 60); do
  if curl -fs "http://127.0.0.1:$PORTA/health" >/dev/null 2>&1; then OK=1; break; fi
  kill -0 "$(cat "$OPENJARVIS_HOME/servidor.pid")" 2>/dev/null || break
  sleep 0.5
done
if [[ $OK -ne 1 ]]; then
  rm -f "$OPENJARVIS_HOME/servidor.pid"
  echo "Falha ao iniciar o servidor. Últimas linhas de dados/servidor.log:" >&2
  tail -n 8 "$OPENJARVIS_HOME/servidor.log" >&2
  echo >&2
  echo "Dica: o OpenJarvis precisa de um motor de modelos rodando. Instale o Ollama" >&2
  echo "(https://ollama.com), baixe um modelo (ollama pull qwen3.5:2b) e rode de novo." >&2
  exit 1
fi
echo "OpenJarvis rodando: http://127.0.0.1:$PORTA   (logs: dados/servidor.log)"
(command -v xdg-open >/dev/null && xdg-open "http://127.0.0.1:$PORTA") || (command -v open >/dev/null && open "http://127.0.0.1:$PORTA") || true
