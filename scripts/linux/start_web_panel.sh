#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f config.env ]; then
  echo "Falta config.env. Crea uno desde config.env.example"
  exit 1
fi

source .venv/bin/activate
exec python web_panel.py
