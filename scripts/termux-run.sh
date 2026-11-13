#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
CONFIG="$HOME/.config/verdugo"
if [ ! -f "$CONFIG/environment" ] || [ ! -f "$CONFIG/endpoints.json" ]; then
  echo 'Ejecuta primero: bash scripts/termux-install.sh' >&2
  exit 2
fi
umask 077
set -a
source "$CONFIG/environment"
set +a
export VERDUGO_ENDPOINTS_JSON="$CONFIG/endpoints.json"
export PORT=8177 BIND_ADDRESS=127.0.0.1
exec node "$ROOT/lib/control-plane.mjs"
