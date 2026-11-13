#!/usr/bin/env bash
set -euo pipefail
umask 077
ROOT=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
ENV_DIR="${VERDUGO_ENV_DIR:-$HOME/.local/share/verdugo/python}"
python3 -m venv "$ENV_DIR"
"$ENV_DIR/bin/python" -m pip install -r "$ROOT/requirements-portfolio.txt"
echo "Dependencias locales instaladas. Esto NO instala los 50 servicios."
printf 'Inicio con el núcleo: VERDUGO_PYTHON=%q bash %q\n' "$ENV_DIR/bin/python" "$ROOT/scripts/termux-run.sh"
printf 'Panel único: http://127.0.0.1:8177/portfolio\n'
