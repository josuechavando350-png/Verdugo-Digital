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

## 5. Claude Code y Codex CLI, en la misma laptop o Codespaces

Desde la raíz del repositorio, `.mcp.json` inicia Verdugo por entrada/salida estándar
con Claude Code. Revisa el proyecto y consulta `/mcp`. Para Codex CLI copia la tabla
de `examples/codex-config.toml` a tu configuración privada y cambia `cwd` por la
ruta absoluta de este checkout. Verifica con `codex mcp list`.

Ambos ejecutan `python -m verdugo --config ~/.verdugo/config.json --state ~/.verdugo/estado.sqlite mcp`.
Verdugo expande `~` incluso cuando el cliente MCP no usa un shell. El tenant por defecto
es `nexus`; fija `--tenant cliente-demo` en los argumentos de una conexión para ese
cliente. Nunca permitas que los parámetros de una herramienta elijan otro tenant.

Para análisis opcionales, carga `source ~/.verdugo/perfiles.env` antes de abrir el
cliente. Codex permite declarar en `env_vars` las variables `VERDUGO_*_PYTHON` que
necesites heredar. Las credenciales reales se mantienen en el entorno privado.
Prueba: «consulta el estado del cliente» o «consulta el reporte de anuncios».
El MCP no puede registrar pagos ni encender clientes.

ChatGPT en el navegador y Claude en la app móvil no leen esta configuración local:
para acceso desde esas superficies hace falta una conexión remota compatible, que
no se construye aquí. Claude Desktop dispone también de configuración local propia;
no es la configuración de Claude Code. No abras este proceso a Internet.

Referencias: [MCP de Codex](https://developers.openai.com/codex/mcp/),
[MCP de Claude Code](https://code.claude.com/docs/en/mcp).

## 6. Instalar perfiles de análisis, solo cuando tú lo pidas

```bash
bash scripts/activar.sh --perfiles
source ~/.verdugo/perfiles.env
python -m verdugo runtime-check
```

Requiere Linux y Python 3.12 para las versiones fijadas. Cada `requirements/runtime*.txt`
se instala con su archivo de restricciones en un entorno independiente bajo
`~/.verdugo/runtimes/` (700). `perfiles.env` tiene modo 600. Para reintentar uno:
`bash scripts/activar.sh --perfiles --perfil analytics`. No se habilita ningún servicio.
El operador sigue revisando `enabled`, `license_reviewed` y `runtime_reviewed` en
su configuración privada antes de ejecutar una biblioteca.

No se ejecuta desde `postCreateCommand` ni desde el motor. Imprime cada fallo, deja
su log privado y termina con error si falla un perfil. `perfiles-install.json` registra
tiempo y tamaño observados por perfil; `runtime-check.json` conserva el inventario.
`runtime-check` comprueba versiones: no garantiza que funcionen todos los binarios,
modelos, navegador o recursos auxiliares. Los perfiles npm, Go, R y servidores nativos
no se instalan con este comando Python; tienen preparación específica en `tests_runtime/`.
Medición en el entorno Linux local de esta entrega (no Codespaces): 32 perfiles,
30 min 43.71 s sumados por perfil, 34,650,744,154 bytes de archivos en entornos
(32.27 GiB), y 127/159 rutas con versiones coincidentes. No equivale a ejecución
verificada. El script evita caché de pip; reserva espacio adicional para descargas
y extracción temporal. No hay una medición observada en Codespaces todavía.

## 7. Importar un reporte de anuncios y consultarlo

Exporta **por día y campaña**, UTF-8, máximo 5 MiB, sin columnas de personas.
Se reconocen encabezados en español e inglés: día, campaña, costo, clics,
impresiones, conversiones y acción de conversión. Google: `Day,Campaign,Cost,Clicks,Impressions,Conversions`.
Meta: `Día,Nombre de la campaña,Importe gastado (MXN),Clics (todos),Impresiones,Resultados`.
Exporta sin separadores de miles; acepta punto o coma decimal y separador CSV coma,
punto y coma o tabulador. Fechas ISO `YYYY-MM-DD`. No admite preámbulos ni filas de totales.

```bash
python -m verdugo --config ~/.verdugo/config.json --state ~/.verdugo/estado.sqlite --tenant cliente-demo ads-import @reporte.csv --platform google --currency MXN
# Revisa y repite con --execute. Datos ficticios: agregar --dataset demo.
python -m verdugo --config ~/.verdugo/config.json --state ~/.verdugo/estado.sqlite --tenant cliente-demo ads-report --start-date 2026-11-01 --end-date 2026-11-15 --compare-start 2026-10-01 --compare-end 2026-10-15 --budget-month 3000
```

Solo `operator` importa. Un cliente apagado no puede importar ni consultar. Las campañas
se presentan con identificadores estables; sus nombres y el CSV nunca se guardan.
Reimportar actualiza las mismas claves diarias, sin duplicar. No elimina campañas ausentes
en un archivo posterior: corrige una fila existente exportando explícitamente su valor,
incluso cero. La moneda y `real`/`demo` siempre quedan separadas.
Desgloses que repitan gasto por acción se rechazan; no se inventa cómo repartirlo.
La acción se usa solo para detectar duplicados; no se retiene su texto ni se equipara a ventas.

El costo por cliente usa ventas `won`, canal `paid`, del libro comercial en el mismo
periodo (hora de Ciudad de México). Son pagos declarados, no conciliación bancaria.
No se atribuye ese costo a una campaña o plataforma sin evidencia. La proyección
mensual usa días completos, exige cobertura desde el día 1 y nunca es una promesa.
Sin perfiles habilitados usa z-score simple; con revisión y versiones correctas puede
usar PyOD y la línea base Naive de StatsForecast. No interpola días faltantes.

Meta directo: revisa en la configuración privada `api_version: v26.0`,
`account_id: act_…`, `account_scope_reviewed: true`, `report_start_date` y
`report_end_date`, además de los permisos habituales. La operación es `insights.summary`,
con `params: {}`. Usa solo lectura y una credencial con permisos mínimos; nunca pegues
el token en el JSON. Consulta `docs/LOTE_A_300.md` para alcance y evidencia.

## 8. Panel local (lote B)

Requiere Python 3.12 y Node 24.22.1. Desde la raíz del repositorio:

```bash
bash scripts/activar.sh --panel --instalar  # instala dependencias fijadas, compila y abre
bash scripts/activar.sh --panel            # siguientes veces; no instala nada
bash scripts/activar.sh --panel --viewer   # consulta, puerto 8767
```

`--solo-instalar` prepara el panel sin dejar un servidor corriendo. Es el mismo
recorrido que ejecuta el job del panel en CI. Si falta Node 24.22.1, prepara esa
versión antes; el script lo comprueba y no instala un runtime distinto por su cuenta.
Los perfiles de análisis siguen siendo opcionales y se cargan con `source ~/.verdugo/perfiles.env`.
La instalación manual equivalente sigue disponible:

```bash
python3.12 -m venv ~/.verdugo/panel-venv
~/.verdugo/panel-venv/bin/python -m pip install --no-cache-dir -r panel/requirements.txt -c panel/constraints.txt
npm ci --prefix panel
npm run build --prefix panel
~/.verdugo/panel-venv/bin/python -m verdugo --config ~/.verdugo/config.json --state ~/.verdugo/estado.sqlite --role operator panel
```

Antes debe existir la configuración privada creada por `scripts/activar.sh`.
Abre `http://127.0.0.1:8766` y copia el token del archivo privado indicado por la
terminal. No lo pongas en la URL ni en Git. El directorio requiere modo 700 y
el token modo 600. El token y los reportes quedan solo en memoria del navegador;
al salir se vacía la sesión. Cierra también pestañas que ya no uses.

Para consulta usa `--role viewer panel --port 8767`; tiene un token separado y
ningún permiso de escritura. No cambies el rol en una sesión ya compartida.
El proceso se enlaza únicamente a 127.0.0.1; no admite otro host de escucha.
En Codespaces abre Ports, agrega 8766 y conserva la visibilidad **Private**.
Solo tú debes poder abrir ese reenvío; no elijas Public. No se despliega nada.

Las pantallas usan el mismo SQLite. Cliente nuevo: usa «Crear cliente» en Clientes,
registra su interruptor (queda apagado), registra el periodo pagado y confirma.
El vencimiento se comprueba también en la mesa comercial y el MCP, aunque cierres el panel.
En Anuncios puedes subir el CSV, revisar agregados y confirmar; la CLI sigue disponible.
En Embudo registra prospectos, etapas y fechas de seguimiento. Para ganar una venta,
declara su pago, costos y evidencia: pago y venta se guardan juntos, sin revisar el banco.
Selecciona Demostración para los ejemplos sintéticos. Producto muestra las 300
piezas libres; 43 componentes siguen sin integración por motivos documentados.

Las descargas JSON/RSS pueden contener datos privados: consérvalas fuera de Git.
La guía integrada está en `/es/operacion/`. No hay llamadas a modelos, CDNs ni
telemetría de navegador. No se ofrece funcionamiento desconectado del motor.
