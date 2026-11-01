#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
if [[ -f "$OPENJARVIS_HOME/servidor.pid" ]]; then kill "$(cat "$OPENJARVIS_HOME/servidor.pid")" 2>/dev/null && echo "Servidor parado."; rm -f "$OPENJARVIS_HOME/servidor.pid"; else echo "Nenhum servidor registrado."; fi
