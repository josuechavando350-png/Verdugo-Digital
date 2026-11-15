# Complemento v0.21 — evidencia y alcance

Base: `a6809de201ba517846e19cf965194b21e6617050`, rama `feat/v0.21-final88`, PR #20.
Se añaden **41 de las 68 integraciones pendientes**: 17 operaciones locales
originales y 24 contratos HTTP. Junto con las 20 anteriores de v0.21, son
61 operaciones de esta tanda y **27 todavía pendientes**. No declarar terminada
la tanda. No se modifica main ni se altera la política de licencias.

Inventario actual: 322 entradas; 217 conectadas bajo la política, 56 componentes,
27 pendientes y 22 excluidas. Hay 102 adaptadores HTTP (106 acciones) y 134
operaciones locales; 19 adaptadores HTTP históricos siguen excluidos por licencia.

## Operaciones comprobadas y límites

| Proyecto | Operación | Alcance |
|---|---|---|
| `a2a` | `tasks.snapshot` | Almacén temporal de tareas con SDK oficial 1.3.0; proyecta estados; no invoca agentes. |
| `anubis` | `health.summary` | Salud del proceso; Basic nativo del puerto de métricas revisado. |
| `autogeo` | `citations.score` | Puntuación de citas sobre tokens y referencias suministrados; no visibilidad real ni efectos causales. |
| `browser-use` | `domains.evaluate` | Evaluación de dominios con DomainRules original; sin navegador ni navegación; no certifica una barrera de seguridad. |
| `c2pa` | `manifest.inspect` | Inspección y validación nativa de manifiesto PNG embebido, sin red; no certifica autenticidad ni confía en firmantes de ejemplo. |
| `claude-skills-c-level` | `cashflow.scenario` | Escenario de caja con calculadora original de CFO; no P&L realizado ni conciliado. |
| `cognee` | `text.segment` | Segmentación original por palabras y límites de oración; sin grafo de conocimiento ni LLM. |
| `comtradeapicall` | `groups.expand` | Expansión original de grupos de países suministrados; sin consultar comercio. |
| `datosmex` | `fix.latest` | Observación más reciente de serie Banxico SF43718; Bmx-Token por encabezado; no cotización ejecutable. |
| `dbt` | `campaigns.materialize` | Seed y modelo SQL fijos sobre DuckDB temporal, ejecutados por dbt Core v1.12.7 oficial; no usa dbt v2 comercial ni almacén externo. |
| `debezium` | `connector.summary` | Estado de un conector Kafka Connect identificado por el operador como Debezium; proxy; no prueba CDC. |
| `gdeltdoc` | `articles.summary` | Primera respuesta pública de artículos sobre un tema configurado; 50 como máximo, 24 h; no cobertura total ni contenido. |
| `google-ads` | `accounts.summary` | Cuentas directamente accesibles; OAuth y developer-token separados; no crea campañas. |
| `gpt-researcher` | `passages.rank` | Ranking BM25 de pasajes suministrados; no búsqueda, LLM ni veracidad semántica. |
| `huginn` | `agents.summary` | Primera página de agentes, habilitados/deshabilitados; cookie de sesión; no ejecuta agentes. |
| `humanlayer` | `health.summary` | Salud reportada de proceso y consultas de base en Riptide API; proxy; no ejecuta agentes. |
| `krayin-crm` | `dashboard.summary` | Recuentos del dashboard nativo en /admin, ventana configurada en el servidor y alcance del usuario; cookie de sesión; sin extensión REST. |
| `letta` | `health.summary` | Salud del App Server oficial Letta Code; fuente complementaria fijada, proxy; no usa el servidor archivado. |
| `lighthouse` | `description.audit` | Auditoría original meta-description sobre artefactos suministrados; sin navegador, rendimiento ni auditoría completa. |
| `livekit` | `rooms.summary` | POST de lectura ListRooms, JWT con roomList, duración 60 s; recuentos de salas/participantes; no medios. |
| `mcp-gsc` | `sites.summary` | Sitios y niveles de permiso reportados por Search Console; OAuth; no publica contenido ni ejecuta MCP. |
| `meridian` | `media.transform` | Adstock geométrico normalizado y Hill con parámetros suministrados; no ajusta MMM ni demuestra causalidad. |
| `meta-ads` | `accounts.summary` | Primera página de cuentas publicitarias y estados; OAuth, API v26.0; no gasto. |
| `nlweb` | `health.summary` | Salud y tiempo activo reportados; proxy; no verifica respuestas de modelos. |
| `opengmb` | `actions.summary` | Catálogo de acciones anunciadas; Bearer nativo; no comprueba permisos efectivos ni ejecuta acciones. |
| `openprospector` | `readiness.summary` | Proveedores configurados y disponibilidad declarada de cola; proxy; no contactos extraídos. |
| `openseo` | `projects.summary` | Recuento de proyectos con clave oseo_; lectura puede actualizar last-used de la clave. |
| `otel-collector` | `metrics.summary` | Uptime del colector con nomenclatura predeterminada revisada; proxy; no acredita entrega de telemetría. |
| `postal` | `health.summary` | Salud del proceso; proxy Bearer obligatorio; no prueba entrega de correo. |
| `praw` | `posts.summary` | Primera página hot de un subreddit configurado; OAuth y acceso gratuito revisado; solo recuentos, sin usuarios/textos. |
| `python-podcastindex` | `index.summary` | Estadísticas agregadas del índice; autenticación SHA1/fecha nativa; sin descargar episodios. |
| `slidev` | `slides.parse` | Parser original de diapositivas, con YAML deshabilitado; sin compilar Vue, cargar recursos o publicar. |
| `storm` | `citations.inspect` | Análisis y retirada de citas numéricas suministradas; no recuperación ni verificación de fuentes. |
| `temporal` | `namespaces.summary` | Primera página de namespaces en el gateway HTTP; proxy; no inicia workflows externos. |
| `tfcausalimpact` | `impact.estimate` | Estimación VI original de serie intervenida frente a control, 30–100 observaciones; revisión explícita de supuestos; sin certificación causal/convergencia. |
| `trendspyg` | `traffic.normalize` | Normalización de etiquetas de volumen como límites inferiores; sin consultar tendencias. |
| `tusd` | `metrics.summary` | Una métrica de conexiones abiertas; proxy obligatorio; no comprueba cargas. |
| `vanna` | `campaigns.query` | SQL fijo con parámetros sobre SQLite temporal; sin generación SQL ni LLM. |
| `wbgapi` | `population.read` | Una observación anual de población, indicador SP.POP.TOTL y país/año configurados; no población actual. |
| `webmention-io` | `mentions.summary` | Primera página privada jf2; Bearer nativo soportado por el código; solo recuentos. |
| `youtube-comment-downloader` | `comments.inspect` | Inspección original de renderers de comentarios suministrados; recuentos de likes/respuestas; no descarga vídeos. |

## Ejecución observada

- Suite de núcleo y contratos: 690 pruebas aprobadas en CPython 3.12.
- 17 operaciones locales originales en un único `product-run`, 18 pasos incluyendo
  instantánea comercial; persistencia y replay después de cerrar/abrir SQLite.
  Vanna alimenta dbt mediante una referencia de workflow.
- Flujo conjunto de las 41 integraciones nuevas: 17 operaciones locales originales
  + 24 respuestas HTTP sintéticas + instantánea comercial, 42 pasos, 123.651 s.
  Cero llamadas HTTP o ejecuciones de worker durante el replay tras reinicio.
  [Evidencia local](evidence/v021-completion-local.json).
- Seis paquetes npm originales probados juntos, incluidos los cuatro anteriores;
  HTML alimenta lint y SEO Graph alimenta el validador de breadcrumbs.
- Los 24 contratos HTTP nuevos tienen transporte loopback y proyección comprobada;
  las 66 lecturas admisibles del producto se prueban juntas con respuestas sintéticas.
- C2PA: PNG firmado de ejemplo, sin manifiesto, contenido alterado y manifiesto remoto.
  Un certificado de ejemplo no se convierte en autenticidad verificada.
- Los ocho perfiles Python pasan `pip check`; dependencias exactas y npm lock fijados.
  Los artefactos instalados se identifican por hashes en
  [evidencia de distribuciones](evidence/v021-completion-artifacts.json).

Estos resultados locales no son aceptación de servicios productivos. Las pruebas
HTTP usan respuestas sintéticas, no cuentas reales. GDELT respondió 503 y la lectura
pública de World Bank agotó el tiempo durante una comprobación puntual; no se usan
esos intentos como pruebas de funcionamiento. La ejecución local aquí usa las
restricciones del worker; el aislamiento de red del sistema operativo corresponde
al workflow de CI, y solo cuenta cuando ese trabajo haya pasado para el commit.

## Preparación reproducible

Engine, CLI y MCP no instalan dependencias. El administrador prepara los perfiles:

```sh
python tests_runtime/install_final.py --group utility021
python tests_runtime/accept_final.py --group utility021
```

Grupos nuevos: `utility021`, `browser021`, `storm021`, `dbt021`, `a2a021`,
`research021`, `meridian021`, `causal021`; `node` añade Slidev y Lighthouse.
Los perfiles se eligen mediante `VERDUGO_<PERFIL>_PYTHON`; npm usa
`VERDUGO_NATIVE_ROOT`. No se permiten rutas, SQL, comandos, modelos, hosts ni
credenciales desde parámetros de una operación. Los perfiles deben ser confiables;
los hooks Python no constituyen aislamiento de código nativo hostil. CI ejecuta
las recetas como usuario sin privilegios y dentro de un namespace sin red.

Los proveedores permanecen deshabilitados. Antes de activarlos se revisan versión,
licencia, autenticación, alcance de cuenta y coste. Un flag de proxy no crea un proxy.
Las lecturas públicas no aceptan token ni origen alternativo. Los JWT de LiveKit y
las firmas de PodcastIndex vinculan las credenciales estables para no invalidar un
replay por cambiar la hora. No se guardan respuestas crudas ni secretos.

## Procedencia

[Contratos y archivos originales](../sources/contracts-v021-completion.json) conserva
commits del catálogo, hashes Git/SHA-256 y fuentes complementarias del SDK A2A,
dbt v1, C2PA Python, Temporal, LiveKit, PodcastIndex y Letta Code. El commit del
catálogo es distinto de la versión de distribución ejecutada. Las 322 identidades
originales y sus 33 archivos de fuentes permanecen intactos.

Los tres módulos Python vendorizados conservan bytes y licencia originales; ambos
hashes se verifican antes de cargarlos. Las fuentes adicionales no se ejecutan
al generar el inventario. Krayin usa rutas MIT del CRM y no su paquete REST sin
licencia; Huginn sí expone agents.json y Webmention sí acepta Bearer según sus
fuentes fijadas, corrigiendo notas anteriores del plan.
