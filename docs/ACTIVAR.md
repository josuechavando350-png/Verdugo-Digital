# Activar Verdugo Digital (300 piezas)

Verdugo es **un solo producto**: una línea de comandos y un servidor MCP sobre el mismo motor (`Engine`), con una base SQLite por empresa, aprobaciones, auditoría y reanudación. Las 300 piezas libres entran por ahí; no se operan por separado.

Activarlo tiene tres niveles. Cada uno es una decisión del operador; nada se enciende solo.

## 1. Abrirlo (gratis, desde el teléfono o una laptop)

**En GitHub Codespaces:** abre `https://codespaces.new/josuechavando350-png/Verdugo-Digital` en Chrome y toca **Create codespace**. Al terminar de crearse corre `scripts/activar.sh --pruebas` automáticamente.

**En cualquier Linux, o en Windows con WSL2:**

```
git clone https://github.com/josuechavando350-png/Verdugo-Digital
cd Verdugo-Digital
bash scripts/activar.sh --pruebas
```

El script:
- crea `~/.verdugo/` (permisos 700) y `config.json` con las 322 entradas **apagadas**;
- corre las pruebas del núcleo;
- muestra el estado del producto y el diagnóstico.

No llama a ningún servicio externo ni instala proveedores.

## 2. Ver el estado en cualquier momento

```
bash scripts/activar.sh
```

O directamente:

```
python3 -m verdugo --config ~/.verdugo/config.json --state ~/.verdugo/estado.sqlite product-status
python3 -m verdugo --config ~/.verdugo/config.json --state ~/.verdugo/estado.sqlite doctor
```

`doctor` responde `not_configured` mientras no haya ningún servicio encendido. Es lo esperado al empezar.

## 3. Encender un servicio

Ejemplo con Uptime Kuma. Funciona igual para cualquier pieza con estado `conectado`.

1. **Ten la instancia funcionando** (tuya o del cliente) y crea en ella una clave de API con permisos mínimos.
2. **Edita `~/.verdugo/config.json`**, en `tenants → nexus → services → uptime-kuma`:
   - `"enabled": true`
   - `"license_reviewed": true`, solo después de leer su licencia;
   - `"version"`: la versión instalada;
   - `"base_url"`: la dirección de tu instancia;
   - los campos `*_reviewed` que pida esa pieza, después de revisarlos.
3. **Pon la clave en una variable de entorno, nunca en el archivo:** `export VERDUGO_NEXUS_UPTIME_KUMA_TOKEN=...`. En Codespaces, usa *Settings → Secrets*.
4. **Revisa el plan** (no llama a nada):
   ```
   python3 -m verdugo --config ~/.verdugo/config.json --state ~/.verdugo/estado.sqlite product-run '{"id":"kuma-001","services":["uptime-kuma"],"dataset":"real","currency":"MXN"}'
   ```
5. **Ejecútalo** agregando `--execute` al mismo comando. Para una lectura nueva usa otro `id`; repetir el mismo `id` reutiliza lo guardado.

Algunas piezas piden datos propios (por ejemplo, Google Ads necesita un *developer token* que Google aprueba aparte y la revisión del permiso OAuth). El archivo de configuración marca cada campo requerido.

## 4. Interruptor por cliente (paga = prendido, no paga = apagado)

Cada cliente es un *tenant* propio, con sus servicios y su historial separados. El interruptor decide si ese tenant recibe servicio:

- **Se registra apagado.** No recibe nada hasta que anotes su primer pago.
- **Prendido** mientras la fecha de hoy (hora de Ciudad de México) no pase de `pagado hasta` + días de gracia.
- **Se apaga solo** al día siguiente de vencer: el motor rechaza cualquier acción de servicio para ese cliente, incluso repetir una ya guardada.
- Tu propio tenant (`nexus`) no tiene interruptor y nunca se apaga.

```bash
V="python -m verdugo --config ~/.verdugo/config.json --state ~/.verdugo/estado.sqlite"

$V tenant-add cliente-1 --execute                                   # crea el cliente con todo apagado
$V --tenant cliente-1 client-register --label "Cliente 1" --grace-days 3 --execute
$V --tenant cliente-1 client-pay --months 1 --execute               # pagó: prendido 1 mes
$V --tenant cliente-1 client-pay --until 2027-01-15 --execute       # o hasta una fecha exacta
$V --tenant cliente-1 client-pause --reason "Sin pago" --execute    # apagarlo ya, aunque tenga días
$V --tenant cliente-1 client-resume --execute                       # quitar la pausa
$V --tenant cliente-1 client-status                                 # ver su estado
$V client-list                                                      # todos los clientes: activos y apagados
```

- Sin `--execute`, cada comando solo muestra la vista previa.
- `--months` suma a partir de la fecha pagada si aún no vence, así un pago adelantado no pierde días.
- Cada cambio queda en la bitácora (`events`) con quién lo hizo.
- Desde Claude o ChatGPT (MCP), la herramienta `verdugo_client_status` **solo consulta**. Anotar pagos y prender o apagar se hace únicamente desde la terminal con rol `operator`, para que ningún asistente pueda prender un cliente por su cuenta.
- El pago lo declaras tú. Verdugo no revisa tu banco ni usa ningún procesador de pagos.

## Qué no hace este paso

- **No despliega nada.** El producto corre donde lo abras: Codespaces se apaga cuando no lo usas, y una laptop depende de la luz y el internet de casa. Para operación de 24 horas hace falta un servidor.
- **No verifica proveedores en vivo** (`live_verified` sigue en 0) hasta que tú enciendas uno y lo ejecutes.
- **No lanza campañas ni envía mensajes.** Las acciones con efecto siguen detrás de aprobación.
- **No abre el proceso a internet:** no lo expongas como servidor público.
- **No usa servicios de pago.**

Los análisis locales (159 rutas) usan perfiles de Python aparte que prepara el administrador. Ver `docs/AMPLIACION_V020.md` y `docs/AMPLIACION_V021.md`.
