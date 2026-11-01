#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="$repo_root/backend/.venv/bin/python"

if [[ ! -x "$python_bin" ]]; then
  printf '%s\n' 'Missing backend/.venv. Follow the installation steps in README.md.' >&2
  exit 1
fi

cd -- "$repo_root/backend"
"$python_bin" -m ruff check .
"$python_bin" -m ruff format --check .
"$python_bin" -m splitbill.openapi --check
