#!/usr/bin/env bash
# Puesta en marcha de Verdugo Digital (300 piezas libres) en un Linux o en GitHub Codespaces.
# Solo --perfiles instala dependencias solicitadas; no habilita servicios: deja el producto
# listo, comprueba que funciona y muestra el estado. Activar un servicio es una decisión del operador.
set -euo pipefail
umask 077

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
PY="${PYTHON:-python3}"
VERDUGO_HOME="${VERDUGO_HOME:-$HOME/.verdugo}"
CONFIG="$VERDUGO_HOME/config.json"
STATE="$VERDUGO_HOME/estado.sqlite"

"$PY" -c 'import sys; assert sys.version_info >= (3, 12), "Se necesita Python 3.12 o superior"'

case "${1:-}" in
  ""|--pruebas) ;;
  --perfiles) shift; exec "$PY" scripts/instalar_perfiles.py "$@" ;;
  --panel) shift; exec bash scripts/panel.sh "$@" ;;
  *) echo "Uso: scripts/activar.sh [--pruebas|--perfiles [--perfil NOMBRE]|--panel [--instalar|--solo-instalar] [--viewer]]" >&2; exit 2 ;;
esac

mkdir -p "$VERDUGO_HOME"
chmod 700 "$VERDUGO_HOME"
if [ ! -f "$CONFIG" ]; then
  "$PY" -m verdugo init --out "$CONFIG" >/dev/null
  chmod 600 "$CONFIG"
  echo "Configuración creada en $CONFIG (todos los servicios apagados)."
else
  echo "Configuración existente conservada: $CONFIG"
fi

if [ "${1:-}" = "--pruebas" ]; then
  echo "Corriendo las pruebas del núcleo (tarda menos de un minuto)..."
  "$PY" -m unittest discover -s tests -q
fi

"$PY" -m verdugo --config "$CONFIG" --state "$STATE" product-status > "$VERDUGO_HOME/estado.json"
# doctor devuelve 1 cuando ningún servicio está configurado; es el estado esperado al empezar.
"$PY" -m verdugo --config "$CONFIG" --state "$STATE" doctor > "$VERDUGO_HOME/doctor.json" || true

"$PY" - "$VERDUGO_HOME/estado.json" "$VERDUGO_HOME/doctor.json" <<'PY'
import json, sys
estado = json.load(open(sys.argv[1]))
doctor = json.load(open(sys.argv[2]))
c = estado['connection_states']
encendidos = sum(1 for s in estado['services'] if s.get('enabled'))
print()
print('VERDUGO DIGITAL: un solo producto')
print(f"  Piezas registradas: {estado['registered']}  (libres: {estado['registered'] - c.get('excluido', 0)})")
print(f"  Conectadas al motor: {c.get('conectado', 0)}  |  Integradas en panel: {c.get('integrado_en_panel', 0)}  |  Piezas de construcción: {c.get('pieza_de_construccion', 0)}")
print(f"  Pendientes: {c.get('pendiente', 0)}  |  Excluidas por licencia: {c.get('excluido', 0)}")
print(f"  Análisis locales implementados: {estado['local_analysis_routes']}  |  Lecturas de servicios: {estado['bounded_observation_routes']}")
print(f"  Servicios encendidos: {encendidos}  |  Verificados en vivo: {estado['live_verified']}")
print(f"  Diagnóstico: {doctor.get('state')}")
print()
print('Siguiente paso: docs/ACTIVAR.md, sección "Encender un servicio".')
PY
