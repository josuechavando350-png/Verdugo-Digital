#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
umask 077
ROOT=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
if ! command -v pkg >/dev/null 2>&1; then
  echo 'Ejecuta este script dentro de Termux (falta pkg).' >&2
  exit 2
fi
pkg install -y nodejs git openssl curl python
node --input-type=module -e 'import {DatabaseSync} from "node:sqlite"; const [major,minor]=process.versions.node.split(".").map(Number); if(major<22 || (major===22 && minor<16))process.exit(1); const db=new DatabaseSync(":memory:"); db.close();'
CONFIG="$HOME/.config/verdugo"
mkdir -p "$CONFIG"
chmod 700 "$CONFIG"
if [ -L "$CONFIG/environment" ] || [ -L "$CONFIG/endpoints.json" ]; then
  echo 'No se aceptan archivos de configuración que sean enlaces simbólicos.' >&2
  exit 2
fi
if [ ! -f "$CONFIG/environment" ]; then
  printf 'VERDUGO_CONTROL_TOKEN=%s\n' "$(openssl rand -hex 32)" > "$CONFIG/environment"
fi
chmod 600 "$CONFIG/environment"
if [ ! -f "$CONFIG/endpoints.json" ]; then printf '{}\n' > "$CONFIG/endpoints.json"; fi
chmod 600 "$CONFIG/endpoints.json"
echo 'Núcleo local preparado: prospectos, eventos y ventas declaradas en SQLite.'
echo 'No se instalaron los diez servidores upstream. No hay envíos externos habilitados.'
echo "Prueba sintética: node $ROOT/scripts/growth-demo.mjs"
echo "Inicio: bash $ROOT/scripts/termux-run.sh"
