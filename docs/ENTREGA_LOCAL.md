# Entrega local de Verdugo Digital · 0.26.0

Producto para un operador en Linux o Codespaces privado. Incluye clientes,
interruptores por pago declarado, importación y análisis de anuncios, prospectos,
seguimientos, ventas, bitácora, copias completas y recuperación. Usa un solo Engine.
No es un SaaS público, ni un sistema que garantice captación o 15 ventas mensuales.

## Instalar el paquete comprobado

En el workflow **Verdugo verification**, job **panel**, descarga el artefacto
`verdugo-local-<commit>` de una revisión donde los **tres workflows** estén verdes.
Contiene el `.tar.gz`, `SHA256SUMS` y `acceptance.json`. GitHub lo conserva 30 días;
guarda una copia del paquete antes de que expire. El PR sigue sujeto a revisión:
no confundir un artefacto de aceptación con una versión aprobada en `main`.

Requisitos del paquete: Linux, Bash, Python **3.12** con `venv`, acceso a PyPI durante
la instalación y espacio para las dependencias del panel. El paquete ya trae el
panel compilado: el operador no necesita Git, Node ni npm. Las versiones y las
restricciones de Python se conservan en `panel/requirements.txt` y `constraints.txt`.

Desde la carpeta que contiene los archivos descargados:

```sh
sha256sum -c SHA256SUMS
tar -xzf verdugo-digital-0.26.0.tar.gz
cd verdugo-digital-0.26.0
python3 -m verdugo.release
bash scripts/activar.sh --panel --instalar
```

La configuración y la base se guardan fuera del paquete, en `~/.verdugo`.
El entorno del panel de este paquete se llama `panel-venv-0.26.0`: una actualización
no reemplaza las dependencias de la versión anterior. La primera instalación deja
los servicios apagados. Para volver a abrirlo: `bash scripts/activar.sh --panel`.
Para lectura: añade `--viewer` (otro token y puerto). Consulta el token en el archivo
privado indicado por el arranque; no lo pegues en una URL ni lo compartas con clientes.

Las sumas detectan cambios o archivos incompletos; **no son una firma digital**.
Descarga únicamente el artefacto de la revisión que has comprobado. No edites el
paquete extraído: su arranque verifica los archivos. Para desarrollar usa el repo.

La instalación desde el repo sigue disponible en [ACTIVAR.md](ACTIVAR.md) y sí
requiere Node 24.22.1. Los perfiles de análisis opcionales se instalan aparte por
petición del operador; el paquete del panel no incluye los 159 entornos de ejecución.

## Operación diaria

1. En **Clientes**, crea un identificador, registra el interruptor y declara su pago.
2. En **Anuncios**, selecciona datos reales o demo, revisa el CSV y confirma la importación.
3. En **Embudo**, registra prospectos, seguimientos y ventas con su evidencia y pago declarado.
4. En **Producto**, revisa el estado de la instalación y crea un respaldo al terminar.

La copia contiene configuración y SQLite de **todos** los clientes. Está sin cifrar,
con directorios 0700 y archivos 0600. Puede contener datos personales y secretos
escritos en la configuración. No incluye claves que solo existan en variables de
entorno, tokens del panel ni perfiles instalados. Conserva esos elementos por
separado. No subas copias sin cifrar a GitHub, ni siquiera a un repositorio privado.
Un respaldo en el mismo disco protege ante errores; no protege de la pérdida del
host. Para cobertura ante pérdida del host, conserva otra copia cifrada fuera de él.

CLI equivalente, sin llamar a proveedores:

```sh
python3 -m verdugo --config ~/.verdugo/config.json --state ~/.verdugo/estado.sqlite backup-product
python3 -m verdugo --config ~/.verdugo/config.json --state ~/.verdugo/estado.sqlite installation-check
```

La segunda orden devuelve 1 si falta una comprobación, incluida una copia íntegra
de las últimas 24 horas. No enciende servicios ni certifica resultados comerciales.
El panel muestra los mismos resultados. Solo el operador puede crear copias;
la restauración no existe en el navegador ni en MCP.

## Recuperar o ensayar la recuperación

Detén el panel, ingress y workers del entorno original. No hagas funcionar dos
copias que puedan ejecutar la misma actividad externa. Elige el directorio que
mostró el respaldo; reemplaza `ID` por ese nombre. El destino debe ser nuevo y su
carpeta padre privada. Ejemplo con un destino dentro de `~/.verdugo`:

```sh
python3 -m verdugo verify-product-backup --directory ~/.verdugo/respaldos.local/ID
python3 -m verdugo restore-product --from ~/.verdugo/respaldos.local/ID --to ~/.verdugo/recuperado
python3 -m verdugo restore-product --from ~/.verdugo/respaldos.local/ID --to ~/.verdugo/recuperado --execute
VERDUGO_HOME="$HOME/.verdugo/recuperado" bash scripts/activar.sh --panel --instalar
```

La primera restauración es solo vista previa. La ejecución nunca sobrescribe el
original. Conserva datos y pagos, apaga servicios e ingress, elimina aprobaciones
anteriores y genera tokens nuevos al iniciar el panel. Primero compara clientes,
ventas, importes y fechas contra la evidencia externa. Solo después revisa de nuevo
los servicios que necesites y sus permisos. Ninguna operación remota se reanuda sola.

Si la copia tiene `running`, `uncertain` o trabajos sin cerrar, la recuperación se
bloquea. Concílialos con evidencia y genera un respaldo nuevo; no borres filas para
forzarla. Una copia antigua tampoco contiene cambios posteriores: contrasta la
actividad real antes de volver a ejecutar cualquier escritura.

## Actualizar y volver atrás

1. Concilia trabajos pendientes, detén la operación y conserva un respaldo íntegro.
2. Descarga el paquete nuevo aprobado y extráelo en otra carpeta. No reemplaces el viejo.
3. Ejecuta su instalador apuntando al mismo `VERDUGO_HOME`. Su entorno Python se
   mantiene separado por versión. Comprueba **Producto** y los datos del cliente.
4. Si falla, detén la nueva versión. Recupera el respaldo anterior en un directorio
   nuevo y usa el paquete anterior con esa copia. Compara cualquier cambio ocurrido
   desde el respaldo antes de continuar. No apuntes un motor viejo a una base que
   haya cambiado de esquema ni descartes ventas nuevas como parte de un rollback.

## Alcance que sí se comprueba

| Comprobación | Evidencia exigida |
|---|---|
| Motor, aislamiento, roles, pagos e importación | Suite de núcleo y API |
| Panel en teléfono, modo lectura y respaldo confirmado | Tres recorridos de navegador |
| Instalar fuera de Git sin ejecutar Node/npm | Aceptación del paquete extraído |
| Recuperar y reiniciar conservando una venta y sus pagos | Aceptación del paquete y prueba de restauración |
| Archivos del paquete completos | Manifiesto SHA-256 y prueba de alteraciones |
| Versiones y bibliotecas originales del catálogo | Workflows runtime y real service de esa revisión |

Se mantienen **244 piezas del motor + 13 del panel = 257** con rutas de uso,
**43 sin una función justificada** y **0 verificadas con cuentas reales**. No se
agregan dependencias para cambiar esos números. Las 43 decisiones están en
[LOTE_B_300.md](LOTE_B_300.md). Las pruebas usan datos sintéticos.

La aceptación del software local no sustituye la revisión del dueño, la prueba con
sus cuentas ni la evidencia de captación. El producto no debe comercializarse como
«300 integraciones productivas», «tráfico garantizado» o «ventas automáticas».
