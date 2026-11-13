#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
umask 077
ROOT=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
if ! command -v pkg >/dev/null 2>&1; then
  echo 'Ejecuta este script dentro de Termux (falta pkg).' >&2
  exit 2
fi
pkg install -y nodejs git openssl curl python
node -e "if(Number(process.versions.node.split('.')[0])<22)process.exit(1)"
CONFIG="$HOME/.config/verdugo"
mkdir -p "$CONFIG"
chmod 700 "$CONFIG"
if [ ! -f "$CONFIG/environment" ]; then
  printf 'VERDUGO_CONTROL_TOKEN=%s\n' "$(openssl rand -hex 32)" > "$CONFIG/environment"
fi
chmod 600 "$CONFIG/environment"
if [ ! -f "$CONFIG/endpoints.json" ]; then printf '{}\n' > "$CONFIG/endpoints.json"; fi
chmod 600 "$CONFIG/endpoints.json"
echo 'Instalado el núcleo de Verdugo para Termux, NO los 10 servidores externos.'
echo "Diagnóstico: bash $ROOT/scripts/termux-doctor.sh"
echo "Inicio: bash $ROOT/scripts/termux-run.sh"
