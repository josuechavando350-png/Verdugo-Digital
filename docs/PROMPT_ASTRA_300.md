# Instrucciones para Astra: terminar Verdugo Digital (300 piezas)

> Escrito el 16 nov 2026 por encargo de Josue, el dueño del producto. El alcance está cerrado en 300 piezas libres. No reabrir el plan de 666 ni los PR #24 y #25.

## Antes de empezar

1. Lee `AGENTS.md` completo. Sus reglas mandan sobre este documento.
2. Lee `README.md`, `docs/ACTIVAR.md` y `docs/PLAN_CONEXION.md`.
3. Ejecuta `python -m unittest discover -s tests -q`. Deben pasar las 731 pruebas.
4. Ejecuta `python -m verdugo connections` y anota el punto de partida:

| Estado | Piezas |
|---|---|
| conectado | 243 |
| pieza_de_construccion (componentes de interfaz) | 56 |
| pendiente (`meta-ads`) | 1 |
| excluido por licencia (fuera de las 300) | 22 |
| live_verified | 0 |

**Qué significa "100%".** Que las 300 piezas libres queden en uso real dentro de un solo producto que Josue pueda operar desde Codespaces o su laptop:

- motor, más perfiles de análisis instalables;
- lectura de anuncios;
- panel;
- interruptor por cliente.

`live_verified` solo sube cuando Josue conecta cuentas reales. No es tarea tuya y nunca se simula.

## Reglas que no se negocian

- **Nada de nombres reales de clientes** en el repo (código, pruebas, fixtures, documentos, commits). Usa `cliente-demo` y datos sintéticos.
- **Sin proveedores de pago** ni excepciones de licencia escritas en nombre de Josue.
- **Sin despliegues:** nada en Vercel, nada de hosting, nada de servidores públicos. El panel escucha solo en `127.0.0.1`. En Codespaces se usa el reenvío de puertos privado.
- **No inflar conteos.** Una pieza cuenta como integrada solo si se usa de verdad en una ruta de código con prueba. Nunca agregues un `import` vacío para subir el número.
- **Interruptor por cliente:** el MCP solo consulta (`verdugo_client_status`). Registrar pagos y prender o apagar clientes queda en la CLI con rol `operator`, y también en el panel con rol `operator` y confirmación. No le des a ningún asistente una herramienta para encender clientes.
- **Pruebas y CI:** cada cambio trae pruebas. CI debe quedar en verde en todas sus revisiones, incluida la de Python 3.14 que detecta conexiones SQLite sin cerrar (cierra cada `Engine` que abras en una prueba).
- **Lotes y PR:** trabaja en dos lotes, cada uno en su rama y su PR hacia `main`. **No hagas merge.** Josue lo revisa con Claude.

---

## Lote A: el motor (Python)

### A1. Perfiles de análisis instalables en Codespaces

Hoy, en un entorno sin los perfiles, solo responden unas cuantas de las 159 rutas locales. Para que Verdugo pueda analizar campañas, hay que poder instalar los perfiles que ya existen en `requirements/`.

- Agrega `scripts/activar.sh --perfiles`. Debe:
  - crear entornos privados en `~/.verdugo/runtimes/` (modo 700), uno por perfil, usando `requirements/runtime*.txt` con sus `*.constraints.txt`;
  - escribir `~/.verdugo/perfiles.env` con las variables `VERDUGO_*_PYTHON` que el motor ya reconoce;
  - correr `runtime-check` e imprimir cuántas de las 159 rutas quedaron disponibles.
- El motor sigue sin instalar paquetes por su cuenta. El que instala es el script, y solo cuando el operador lo pide.
- No lo metas en `postCreateCommand`, porque es pesado. Documenta en `docs/ACTIVAR.md` cuánto tarda y cuánto ocupa (lo que observes en Codespaces, sin estimar).
- Si un perfil no instala en Codespaces, repórtalo con el error real. No lo ocultes.

### A2. Importar y analizar reportes de anuncios (sin token de desarrollador)

Un cliente puede exportar un CSV desde Google Ads o desde el Administrador de anuncios de Meta. Verdugo debe convertir ese archivo en un diagnóstico.

**Importación.** Nueva operación `ads.import`, con su CLI:

```
--tenant cliente-demo ads-import @reporte.csv --platform google|meta [--execute]
```

- Funciona por tenant, solo con rol `operator` y con vista previa por defecto.
- Acepta un archivo local de máximo 5 MiB. Las columnas reconocidas son día, campaña, costo, clics, impresiones, conversiones y acción de conversión. Admite encabezados en español e inglés de ambas plataformas, y rechaza columnas desconocidas que parezcan datos personales.
- Guarda **solo agregados diarios por campaña** en SQLite. Nunca guarda el archivo crudo, ni rutas, ni datos personales.
- Es idempotente: reimportar el mismo periodo no duplica.

**Reporte.** Nuevo comando `ads-report`, más una herramienta MCP **de solo lectura** `verdugo_ads_report`. Entrega:

- gasto, clics, conversiones y costo por conversión, por periodo y por campaña;
- comparación entre dos periodos;
- ritmo de gasto contra un presupuesto mensual que el operador declara (`--budget-month`), con la proyección al cierre del mes;
- días anómalos: con `pyod` si su perfil está disponible; si no, un z-score simple etiquetado como tal;
- una línea base con `statsforecast` si está disponible;
- **costo real por cliente:** gasto entre ventas `won` del canal `paid` del libro comercial. El reporte debe distinguir siempre "conversión de la plataforma" (un clic a WhatsApp, una llamada) de "cliente que pagó".

**Pruebas.** Fixtures sintéticos de Google y de Meta. Cubrir:

- columnas en español y en inglés;
- archivos malformados;
- límites de tamaño;
- idempotencia;
- aislamiento por tenant;
- que un tenant con el interruptor apagado no pueda importar ni ver reportes;
- que el reporte nunca llame "clientes" a las conversiones.

### A3. `meta-ads`: de pendiente a conectado

Se retiró en la v0.21.1 porque el contrato usaba Bearer y los SDK oficiales de Meta mandan `access_token` en la URL.

- Implementa una sola lectura acotada de insights de la cuenta, tomada del SDK oficial en el commit fijado en `sources/`:
  - campos fijos;
  - versión de API fijada;
  - cuenta y rango de fechas leídos desde la configuración, **nunca** desde `params`.
- El `access_token` va en la consulta, igual que en el SDK. Debe quedar fuera de planes, fingerprints, eventos, SQLite, errores y logs. Sigue el patrón privado de `token_auth` de Matomo.
- Guarda solo recuentos y agregados.
- Agrega pruebas de contrato y evidencia en el documento de la versión. `conectado` sale del código; no se escribe a mano en el mapa.

### A4. Usarlo con Claude y ChatGPT (sin servidor público)

- Agrega un `.mcp.json` de ejemplo para Claude Code y un fragmento de configuración para Codex CLI. Ambos lanzan:

```
python -m verdugo --config ~/.verdugo/config.json --state ~/.verdugo/estado.sqlite mcp
```

- Documenta en `docs/ACTIVAR.md`, sección 5, cómo usar Verdugo desde Claude Code y desde Codex dentro de Codespaces o en la laptop.
- Aclara que ChatGPT en el navegador y Claude en la app necesitan un MCP remoto. Eso **no** se construye en este lote; requiere una decisión aparte de Josue.

### Entrega del lote A

Un PR con:

- el conteo antes y después (`connections`, `runtime-check` en Codespaces);
- la lista de comandos nuevos;
- el número de pruebas.

Todo con números observados.

---

## Lote B: Verdugo Panel (los 56 componentes)

Los 56 componentes (`kind: componente`) son piezas de interfaz y de API. Se conectan al programar la plataforma, no a través del motor. Este lote construye el panel de Verdugo usándolos de verdad.

### B1. Qué es el panel

Es una aplicación local en `panel/`, en español, pensada para usarse desde el teléfono (pantallas angostas primero). Lee y escribe solo a través del mismo `Engine`, con sus mismos roles; no tiene una base de datos propia.

Pantallas mínimas:

1. **Clientes:** el interruptor de cada uno (prendido o apagado, días restantes, motivo). Los botones "Registrar pago", "Pausar" y "Reanudar" requieren rol `operator` y una confirmación explícita.
2. **Anuncios:** gráficas de `ads-report` (gasto, conversiones, costo por conversión, ritmo contra presupuesto, días anómalos).
3. **Embudo comercial:** identificados, contactados, reuniones, propuestas, ganados y perdidos, con el costo por cliente.
4. **Estado del producto:** las 300 piezas por estado, perfiles disponibles y diagnóstico (`doctor`).
5. **Bitácora:** eventos recientes del tenant.

**Seguridad:**

- escucha en `127.0.0.1`;
- token local en `~/.verdugo` (modo 600);
- protección CSRF en las escrituras;
- sin CORS abierto;
- sin telemetría hacia terceros;
- sin despliegue.

### B2. Cómo cuenta un componente como integrado

- Crea un manifiesto verificable, por ejemplo `verdugo/panel_components.py` o `sources/panel.json`. Por cada componente registra: versión fijada (tomada del commit fijado en `sources/`), archivo donde se usa y prueba que lo ejercita.
- Haz que `connections` calcule un estado nuevo, `integrado_en_panel`, a partir de ese manifiesto. Una prueba de integridad debe fallar si el componente no aparece en el `package.json` o en el lock con esa versión, o si no se usa en el código señalado.
- Usa como columna vertebral los que encajan naturalmente, por ejemplo:
  - interfaz: `nextjs` o `astro`, `tailwindcss`, `shadcn-ui`;
  - datos y gráficas: `tanstack-query`, `tanstack-table`, `echarts`;
  - API y validación: `hono` o `fastapi`, `zod`;
  - idioma: `i18next`;
  - pruebas: `vitest`.
- Para los demás, busca un uso real y pequeño que aporte al panel. Ejemplos: `pdfme` para exportar el reporte del cliente en PDF, `driverjs` para el recorrido inicial, `web-vitals` para medir el propio panel, `maplibre` para clientes por zona, `libphonenumber` para validar teléfonos.
- **Si un componente no tiene un uso honesto** (por ejemplo `expo`, `kepler-gl`, `bpmn-js`, `squiggle`, `onlinewardleymaps`, `id-openstreetmap`, `marimo` o `hoppscotch`), déjalo como `pieza_de_construccion` y escribe por qué en el documento del lote. Un 52/56 honesto vale más que un 56/56 inflado.

### B3. Pruebas del panel

- `vitest` para la interfaz.
- Una prueba de extremo a extremo con datos sintéticos que:
  1. registra un cliente;
  2. comprueba que aparece apagado;
  3. registra el pago y ve que se prende;
  4. adelanta el reloj y ve que se apaga;
  5. verifica que un rol `viewer` no ve los botones de escritura.
- CI agrega un job para el panel sin romper los existentes.

### Entrega del lote B

Un PR con:

- capturas del panel en pantalla de teléfono;
- la tabla de los 56 componentes (integrado o no, y por qué);
- el conteo final de `connections`;
- las pruebas.

---

## Cómo reportarle a Josue

Al terminar cada lote, escribe un resumen corto, en español sencillo y sin tecnicismos:

- qué quedó funcionando;
- qué números cambiaron;
- qué no se pudo hacer y por qué;
- qué le toca hacer a él, por ejemplo abrir Codespaces o conectar una cuenta real para que `live_verified` deje de ser 0.

No afirmes despliegues, resultados comerciales ni verificaciones que no hayas observado.
