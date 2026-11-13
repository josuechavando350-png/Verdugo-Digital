# Ejecutar el núcleo en Termux

El desarrollo queda en GitHub. No se instala ni contrata alojamiento remoto.
Esto instala el núcleo comercial local, **no los diez servidores originales**.
La compatibilidad final con el teléfono todavía requiere ejecutar esta prueba.

## Instalación nueva, sin tocar una copia anterior

```sh
pkg update -y
pkg install -y git
cd "$HOME"
git clone --single-branch --branch feat/growth-engine-ten-clean-20261112 https://github.com/josuechavando350-png/Verdugo-Digital.git Verdugo-Digital-growth
cd Verdugo-Digital-growth
bash scripts/termux-install.sh
bash scripts/termux-doctor.sh
node scripts/growth-demo.mjs
bash scripts/termux-run.sh
```

No se descargan los diez submódulos al instalar. Clonarlos no inicia sus servicios.
El instalador exige Node >=22.16 y comprueba `node:sqlite`, sin paquetes NPM.
Si esa capacidad no está disponible, la instalación se detiene; no se informa
éxito ni se inventa compatibilidad de Android.

Abrir `http://127.0.0.1:8177` desde el mismo teléfono. El servidor corre en primer
plano y se detiene con Ctrl+C; no es un servicio 24/7 certificado. Android puede
interrumpir procesos. La base SQLite persiste fuera del repositorio, pero esto
no garantiza disponibilidad continua ni sustituye un respaldo.

Para leer el token en otra sesión local de Termux:

```sh
sed -n 's/^VERDUGO_CONTROL_TOKEN=//p' "$HOME/.config/verdugo/environment"
```

Introducirlo en el panel. No publicarlo ni compartirlo en el chat. No se almacena
en localStorage del navegador. Cerrar o recargar la página obliga a introducirlo
otra vez. El panel permite captar prospectos, modificar etapas, registrar ventas
declaradas y actualizar consentimiento.

## Rutas privadas

- Configuración: `~/.config/verdugo/`, permisos 0700; archivos 0600.
- Base: `~/.local/share/verdugo/growth.sqlite`, fuera de Git.
- `VERDUGO_STATE_DB`, `VERDUGO_WORKSPACE` y `PORT` permiten una configuración local
  distinta. El token se aplica al espacio configurado, no al elegido por una petición.

No hay proveedores habilitados por defecto ni envíos al iniciar. No añada secretos
a archivos del repositorio. Los contratos y límites están en [GROWTH_CORE.md](GROWTH_CORE.md).

## Pruebas

```sh
node --test tests/*.test.mjs
python -m unittest discover -s tests -p 'test_*.py' -v
node scripts/growth-demo.mjs
```

La demo es sintética, usa una base temporal, la reabre para comprobar persistencia
y la elimina al terminar. No representa clientes reales, ingresos o capturas.
Las pruebas de adaptadores usan servidores HTTP locales de prueba, no proveedores
auténticos. `node scripts/termux-status.mjs --require-ten-live` seguirá fallando
correctamente mientras no exista aceptación E2E real de los diez.
