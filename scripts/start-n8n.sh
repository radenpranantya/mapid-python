#!/usr/bin/env bash
# Start n8n for Session 2 with required n8n 2.x settings (Execute Command + file access).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SESSION2="$ROOT/session-2"

if [ -d "/opt/homebrew/opt/node@20/bin" ]; then
  export PATH="/opt/homebrew/opt/node@20/bin:$PATH"
fi

export NODES_EXCLUDE='[]'
export N8N_RESTRICT_FILE_ACCESS_TO="$HOME/.n8n-files;$SESSION2"

echo "Node: $(node -v)"
echo "NODES_EXCLUDE=$NODES_EXCLUDE"
echo "N8N_RESTRICT_FILE_ACCESS_TO=$N8N_RESTRICT_FILE_ACCESS_TO"
echo "Open http://localhost:5678"
echo ""

exec n8n start
