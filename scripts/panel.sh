#!/usr/bin/env bash
# Explicit panel installation and loopback startup. No providers are enabled.
set -euo pipefail
umask 077
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
PY="${PYTHON:-python3}"
VERDUGO_HOME="${VERDUGO_HOME:-$HOME/.verdugo}"
export VERDUGO_HOME
INSTALL=false
ROLE=operator
PORT=8766
while [ "$#" -gt 0 ]; do
  case "$1" in
    --instalar) INSTALL=true; shift ;;
    --solo-instalar) INSTALL=true; shift; ONLY_INSTALL=true ;;
    --viewer) ROLE=viewer; PORT=8767; shift ;;
    *) echo 'Uso: scripts/activar.sh --panel [--instalar|--solo-instalar] [--viewer]' >&2; exit 2 ;;
  esac
done
PREBUILT=false
VENV_NAME=panel-venv
if [ -f RELEASE.json ]; then
  "$PY" -m verdugo.release
  PREBUILT=true
  VENV_NAME="panel-venv-$("$PY" -c 'from verdugo import __version__; print(__version__)')"
fi
if [ ! -f "$VERDUGO_HOME/config.json" ]; then bash scripts/activar.sh; fi
PANEL_PY="$VERDUGO_HOME/$VENV_NAME/bin/python"
if "$INSTALL"; then
  "$PY" -c 'import sys; assert sys.version_info[:2] == (3,12), "El panel fijado requiere Python 3.12"'
  if ! "$PREBUILT" && [ "$(node --version)" != 'v24.22.1' ]; then echo 'Usa Node 24.22.1 para el panel fijado.' >&2; exit 2; fi
  "$PY" - "$VERDUGO_HOME" "$VENV_NAME" <<'PY'
import os, sys
from pathlib import Path
root=Path(sys.argv[1]).expanduser()
for path in (root, root/sys.argv[2]):
    if path.is_symlink(): raise SystemExit('El directorio privado no puede ser un enlace')
    path.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.stat().st_uid != os.getuid(): raise SystemExit('Directorio de otro usuario')
    path.chmod(0o700)
PY
  "$PY" -m venv --copies "$VERDUGO_HOME/$VENV_NAME"
  "$PANEL_PY" -m pip install --disable-pip-version-check --no-cache-dir -r panel/requirements.txt -c panel/constraints.txt
  "$PANEL_PY" -m pip check
  if ! "$PREBUILT"; then
    npm ci --prefix panel
    npm run build --prefix panel
  fi
fi
if [ ! -x "$PANEL_PY" ] || [ ! -f panel/dist/index.html ]; then
  echo 'Falta preparar el panel. Ejecuta: bash scripts/activar.sh --panel --instalar' >&2; exit 2
fi
if [ "${ONLY_INSTALL:-false}" = true ]; then
  echo 'Panel instalado. Para abrirlo: bash scripts/activar.sh --panel'; exit 0
fi
if [ -f "$VERDUGO_HOME/perfiles.env" ]; then
  echo 'Para análisis opcionales, carga antes tu archivo privado perfiles.env.'
fi
exec "$PANEL_PY" -m verdugo --config "$VERDUGO_HOME/config.json" --state "$VERDUGO_HOME/estado.sqlite" --role "$ROLE" panel --port "$PORT"
