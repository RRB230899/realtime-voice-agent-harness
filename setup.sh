#!/usr/bin/env bash
# One-time local setup: creates the venv and installs dependencies.
# Run from the project root:  ./setup.sh
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  echo "Created .venv"
fi

source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Fill in your credentials."
fi

echo "Setup complete. Activate with: source .venv/bin/activate"
