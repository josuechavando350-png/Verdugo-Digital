#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
echo '=== VERDUGO: TERMUX DOCTOR ==='
echo "Arquitectura: $(uname -m)"
if command -v node >/dev/null; then node --version; else echo 'Node.js ausente'; fi
if command -v git >/dev/null; then git --version; else echo 'Git ausente'; fi
if [ -r /proc/meminfo ]; then
  awk '/MemTotal:/{printf "RAM total: %.1f GB\n",$2/1048576} /MemAvailable:/{printf "RAM disponible: %.1f GB\n",$2/1048576}' /proc/meminfo
fi
df -h "$HOME" | tail -n 1
node "$ROOT/scripts/termux-status.mjs" || true
echo 'Este diagnóstico NO certifica la integración de los diez sistemas.'
