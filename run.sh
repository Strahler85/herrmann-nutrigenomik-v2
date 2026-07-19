#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "🧬 Herrmann Nutrigenomik V2 — getbased-style"
echo ""

# Activate venv
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

PORT=${PORT:-5001}
echo "🌐 Server: http://localhost:$PORT"
echo ""

exec python3 server.py
