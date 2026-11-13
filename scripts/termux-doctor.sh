#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
echo '=== VERDUGO: TERMUX DOCTOR ==='
echo "Arquitectura: $(uname -m)"
node --version
git --version
node --input-type=module -e 'import {DatabaseSync} from "node:sqlite"; const db=new DatabaseSync(":memory:"); db.close(); console.log("SQLite nativo: disponible");'
if [ -r /proc/meminfo ]; then
  awk '/MemTotal:/{printf "RAM total: %.1f GB\n",$2/1048576} /MemAvailable:/{printf "RAM disponible: %.1f GB\n",$2/1048576}' /proc/meminfo
fi
df -h "$HOME" | tail -n 1
node "$ROOT/scripts/termux-status.mjs"
echo 'Disponibilidad de SQLite no certifica el teléfono ni los diez proveedores.'
