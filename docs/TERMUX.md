# Verdugo Digital — Termux (Android sin root)

Este procedimiento instala **solo el núcleo local** de Verdugo Digital y un panel de estado para diez proyectos. No instala PostHog, GrowthBook, erxes, Mautic, Dittofeed, RudderStack, OpenReplay, Twenty, Countly ni Formbricks. La referencia a esos diez repositorios sigue fija en `upstream/` como Git submodules: **referencia al código no significa servicio operativo**.

## Instalar en el móvil

Abrir Termux y ejecutar:

```sh
pkg update -y
pkg install -y git
cd "$HOME"
git clone --single-branch --branch feat/growth-engine-ten-clean-20261112 https://github.com/josuechavando350-png/Verdugo-Digital.git
cd Verdugo-Digital
bash scripts/termux-install.sh
bash scripts/termux-doctor.sh
bash scripts/termux-run.sh
```

El panel estará en **http://127.0.0.1:8177**, solo desde el propio teléfono. Requiere el token creado localmente en `~/.config/verdugo/environment` (permiso 600). No publicar ese archivo ni los endpoints privados.

Los submódulos upstream **no se descargan** durante la instalación, ya que hacerlo consume muchos recursos y no instala sus servidores ni sus bases de datos.

## Verificar

```sh
node --test tests/*.test.mjs
python -m unittest discover -s tests -p 'test_*.py' -v
node scripts/termux-status.mjs
```

Para obtener JSON: `node scripts/termux-status.mjs --json`. El modo `--require-ten-live` falla correctamente con código 2 mientras falte cualquier endpoint **o** una verificación E2E auténtica. Un endpoint HTTP 200 solo indica conectividad básica.

## Conexiones configurables

El archivo privado `~/.config/verdugo/endpoints.json` admite URLs **de salud** de sistemas que realmente estén en ejecución y bajo tu control. Ejemplo estructural (el dominio no es real):

```json
{"posthog":"https://tu-servidor.example/health"}
```

Solo se admite HTTPS, salvo HTTP al propio bucle local 127.0.0.1. Un token o contraseña **nunca** debe colocarse en la URL. Esta versión no implementa autenticación de cada API ni sincronización de datos; solo informa sobre disponibilidad.

## Limitaciones no negociables

Instalar diez servicios upstream íntegros en un teléfono con Termux convencional no es un objetivo compatible garantizable: varios están diseñados para Docker/Kubernetes, x86_64, múltiples bases de datos y cantidades altas de RAM y almacenamiento. PRoot no aporta cgroups ni namespaces reales. No se instalarán infraestructuras remotas sin autorización.

La rama `main` y el respaldo `backup/pre-growth-ten-20261112` se conservan hasta que exista aceptación real de un producto único, con protección de datos, sincronización de identidad y pruebas E2E.
