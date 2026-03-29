#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip ffmpeg
else
  echo "No se detecto apt-get. Instala manualmente: python3, python3-venv, python3-pip, ffmpeg"
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

mkdir -p runtime

if [ ! -f config.env ]; then
  cp config.env.example config.env
  echo "Se creo config.env desde config.env.example. Editalo antes de arrancar."
fi

echo "Instalacion lista."
