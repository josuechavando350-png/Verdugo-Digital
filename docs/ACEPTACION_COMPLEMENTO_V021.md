# Complemento v0.21 — evidencia y alcance

> **Corrección v0.21.1 (revisión):** `google-ads` conserva su lectura con evidencia original añadida (`googleapis/googleapis@97f6460c35`: ruta REST `GET /v26/customers:listAccessibleCustomers` en `customer_service.proto`; encabezado `developer-token` en `google/ads/googleads/interceptors/metadata_interceptor.py` de google-ads-python). `meta-ads` vuelve a pendiente: los SDK oficiales de Meta (Python, Node, PHP, Java y Ruby) envían `access_token` en la URL y ninguno respalda el encabezado Bearer que usaba el contrato. Quedan 87 operaciones de la tanda, 25 contratos HTTP nuevos y 1 pendiente.

Base: `a6809de201ba517846e19cf965194b21e6617050`, rama `feat/v0.21-final88`, PR #20.
Se añaden **68 de las 68 integraciones pendientes**: 41 operaciones locales
con código original, una comparación propia de reglas NAP originales y 26 contratos HTTP. Junto con las 20 anteriores de v0.21, son
88 operaciones de esta tanda y **0 pendientes de implementación**. La aceptación
exige los tres workflows completos sobre el commit vigente. No se modifica main ni se altera la política de licencias.

Inventario actual (tras la corrección): 322 entradas; 243 conectadas bajo la política, 56 componentes,
1 pendiente (`meta-ads`) y 22 excluidas. Hay 103 adaptadores HTTP (107 acciones) y 159
operaciones locales; 19 adaptadores HTTP históricos siguen excluidos por licencia.

## Operaciones comprobadas y límites

| Proyecto | Operación | Alcance |
|---|---|---|
| `playwright-mcp` | `document.snapshot` | Herramienta browser_snapshot del MCP original 0.0.85, cliente SDK 1.32.2 y Chromium 158.0.8127.18; solo recuentos de documento suministrado, JavaScript de página deshabilitado, sin navegación externa. |
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
| `meta-ads` | — | Retirado en la corrección v0.21.1: contrato Bearer sin respaldo en los SDK originales; vuelve a pendiente. |
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

| `promptfoo` | `response.check` | Aserción original contains-all sobre una respuesta suministrada, con proveedor local fijo; cero llamadas a modelos; no evalúa veracidad ni calidad semántica. |
| `log4brains` | `decisions.inspect` | Parser original sobre decisiones suministradas convertidas en ADR temporales; cuenta estados; no consulta ni modifica un repositorio externo. |
| `pricesensitivitymeter` | `prices.survey` | Van Westendorp no ponderado de 5–100 respuestas; puntos descriptivos de la encuesta, no precio óptimo de ingresos ni muestra representativa. |
| `robyn` | `media.transform` | Adstock geométrico y saturación Hill originales en R; parámetros suministrados; no entrenamiento, causalidad ni optimización de presupuesto. |
| `newsjack` | `rewrite.compare` | Comparador léxico original de cifras, fechas, citas, enlaces y entidades entre textos; no comprueba hechos ni equivalencia semántica. |
| `kingfisher-collect` | `releases.inspect` | FileItem, Validate y Pluck originales para metadatos suministrados; deduplica archivo/número conservando el primero; no descarga ni valida el esquema OCDS completo. |

| `openhands` | `health.summary` | Salud del Agent Server oficial 1.62.0; proxy autenticador obligatorio; no ejecución de agentes ni inicialización completa. |
| `valkey` | `cache.match` | MSET/MGET originales sobre claves y números suministrados, en caché temporal; no caché permanente. |
| `postgres` | `campaigns.aggregate` | PostgreSQL 18.7 original, COPY y agregación SQL fija de campañas suministradas; no almacén productivo ni P&L conciliado. |
| `pgvector` | `vectors.rank` | Operador L2 original sobre vectores tridimensionales suministrados; no embeddings generados ni relevancia semántica. |
| `apache-age` | `graph.degrees` | Cypher original parametrizado para grados de salida de grafo suministrado; no conocimiento externo. |

| `openapi-generator` | `spec.validate` | Validador original 7.27.0 sobre OpenAPI 3.0 JSON suministrado; referencias locales; no genera código ni comprueba una API desplegada. |
| `arx` | `groups.anonymize` | ARX 3.9.2 generaliza dos atributos suministrados con k-anonimato y cero supresión; solo devuelve tamaños de clases, nunca filas; no elimina todos los riesgos de reidentificación. |
| `cc-webgraph` | `adjacency.merge` | CountingMergedIntIterator original, compilado sin cambios con WebGraph/fastutil; fusiona adyacencias ordenadas y cuenta repeticiones; no descarga el grafo Common Crawl. |
| `goaccess` | `requests.summarize` | Parser GoAccess 1.7 original sobre eventos suministrados transformados a COMMON; recuentos HTTP y bytes; no mide visitantes reales ni consulta archivos de logs externos. |
| `census` | `tables.summary` | Catálogo público fijo de tablas ACS5 profile 2024; no envía claves ni consulta población. |

| `cua` | `actions.normalize` | Serializadores y dataclasses originales; cambio único de import de tipos; no ejecuta acciones ni accede al escritorio. |
| `tinytroupe` | `experiments.compare` | Welch original y estadísticas descriptivas; logger adaptado, fórmulas intactas; revisión explícita de supuestos; no simula agentes ni prueba causalidad. |
| `local-seo-skills` | `nap.compare` | Comparación propia de reglas NAP exactas de la fuente original; no programa upstream ni MCP; no consulta directorios ni mide ranking. |
| `google-maps-scraper` | `places.inspect` | EntryFromJSON y Validate originales compilados, cargas suministradas; solo recuentos/rating; no consulta Google Maps ni verifica reseñas. |
| `quarto` | `document.render` | Quarto 1.11.9 original convierte secciones de texto plano en HTML pasivo; sin ejecución de código, includes, red ni publicación. |
| `auto-editor` | `audio.levels` | Auto-Editor 31.9.0 original mide amplitudes PCM mono suministradas, máximo un segundo; no edita ni transcribe audio. |

| `microsandbox` | `image.inspect` | CLI original 0.7.15 importa e inspecciona una imagen Docker de textos suministrados; comprueba digest y tamaño nativos; sin VM, KVM, cloud ni caché persistente. |
| `landscape-app` | `landscape.validate` | Validador original sobre metadatos de proyectos suministrados; conserva fallos; solo se adapta la ruta del archivo de errores; sin llamadas a GitHub ni verificación de repositorios. |

| `siteone-crawler` | `pages.crawl` | Crawler original 2.5.1.20260627 descubre enlaces en páginas generadas de datos suministrados, servidas en loopback privado; devuelve visitadas/404, no scores ni rastreo remoto. |
| `sherlock` | `responses.classify` | Sherlock 0.16.2 clasifica respuestas suministradas por código HTTP o marcador literal a través de un servidor privado; no busca personas ni verifica cuentas reales. |

## Ejecución observada

- Suite de núcleo y contratos: 715 pruebas aprobadas en CPython 3.12.
- Las 38 operaciones locales originales y la comparación de reglas NAP participan en el flujo conjunto siguiente.
  Vanna alimenta dbt mediante una referencia de workflow; los resultados persisten en SQLite.
- Flujo conjunto de las 65 integraciones nuevas: 38 operaciones con código original
  + una comparación de reglas NAP + 26 respuestas HTTP sintéticas + instantánea comercial, 66 pasos, 303.292 s.
  Cero llamadas HTTP o ejecuciones de worker durante el replay tras reinicio.
  [Evidencia local](evidence/v021-completion-local.json).
- Ocho paquetes npm originales probados juntos, incluidos los cuatro anteriores;
  aceptación del grupo en 103.895 s. Cuatro casos negativos comprueban que Promptfoo
  conserva fallos de aserción y trata plantillas y referencias de archivo como texto;
  HTML alimenta lint y SEO Graph alimenta el validador de breadcrumbs.
- Los 26 contratos HTTP nuevos tienen transporte loopback y proyección comprobada;
  las 68 lecturas admisibles del producto se prueban juntas con respuestas sintéticas.
- C2PA: PNG firmado de ejemplo, sin manifiesto, contenido alterado y manifiesto remoto.
  Un certificado de ejemplo no se convierte en autenticidad verificada.
- Los nueve perfiles Python pasan `pip check`; dependencias exactas y npm lock fijados.
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
`research021`, `meridian021`, `causal021`, `finalpy021`; `node` añade Slidev, Lighthouse, Promptfoo y Log4brains. `r021` prepara el intérprete R 4.2.2 original extraído de paquetes Debian fijados por SHA-256, sin scripts de instalación privilegiados. Se verifican 793 archivos de ese runtime y cada fuente original. Es un perfil Linux amd64, no una promesa de compatibilidad Android.
Los perfiles se eligen mediante `VERDUGO_<PERFIL>_PYTHON`; npm usa
`VERDUGO_NATIVE_ROOT` y R usa `VERDUGO_R_ROOT`. No se permiten rutas, SQL, comandos, modelos, hosts ni
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

Los cinco módulos Python vendorizados conservan bytes y licencia originales; ambos
hashes se verifican antes de cargarlos. Las fuentes adicionales no se ejecutan
al generar el inventario. Krayin usa rutas MIT del CRM y no su paquete REST sin
licencia; Huginn sí expone agents.json y Webmention sí acepta Bearer según sus
fuentes fijadas, corrigiendo notas anteriores del plan.

Las fuentes R y sus licencias se describen en [contracts-v021-r.json](../sources/contracts-v021-r.json). Se cargan funciones originales concretas, sin instalar los paquetes R completos ni sus rutas de modelos, gráficos o encuestas ponderadas. El intérprete R es una dependencia, no una nueva entrada del catálogo.

El checkpoint `7c38cb72bd5930a5c45821bc8b76ffaf01780ac8` aprobó los tres workflows: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43670439952), [runtimes](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43670439947) y [servicios originales](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43670440002). Esos resultados corresponden al checkpoint de 41, y no sustituyen el CI del nuevo commit de 47.

El checkpoint de 47, `4a0afe938dc926af6326baa261c623d62221430a`, aprobó los tres workflows: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43674427802), [runtimes](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43674427842) y [servicios originales](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43674427831). El fallo anterior de R era `libblas.so.3` ausente: se añadieron BLAS, LAPACK, gfortran y quadmath oficiales fijados por hash. Ese CI no sustituye la aceptación del nuevo perfil de bases de datos.

El perfil `database021` compila Valkey, PostgreSQL, pgvector y AGE originales con fuentes fijadas. En este host se ejecutaron los cuatro mediante `product-run`, con reinicio/replay; el grupo completo pasó en 21.682 s e incluye rechazo de clientes TCP sin contraseña y cierre de los servidores. Por defecto usa sockets Unix privados, sin TCP. Este host rechaza AF_UNIX: el administrador seleccionó `VERDUGO_DATABASE_LOOPBACK=1`, que enlaza únicamente 127.0.0.1 con contraseñas efímeras. Los parámetros nunca eligen destino, puerto, credencial, SQL ni Cypher. CI conserva el modo Unix en namespace sin red. `VERDUGO_DATABASE_ROOT` identifica el perfil. Los datos temporales se borran; Engine/SQLite conserva los resultados. [Fuentes](../sources/contracts-v021-database.json) y [artefactos ejecutados](evidence/v021-database-artifacts.json).

El perfil `tools021` prepara Eclipse Temurin 21.0.13+9, OpenAPI Generator 7.27.0, ARX 3.9.2, WebGraph 3.6.12, fastutil-core 8.5.19 y GoAccess 1.7 con hashes de archivos/distribuciones fijados. El puente Java es propio y llama a algoritmos originales; el iterador de Common Crawl conserva su fuente sin modificaciones. Se verifican 114 archivos del runtime y los archivos fuente. La política Java bloquea conexiones, escuchas y procesos hijos, además del namespace sin red de CI. Java 21 se fija explícitamente: no se presume compatibilidad con versiones que retiren SecurityManager. GoAccess usa configuración fija sin DNS. El grupo completo pasó en 100.086 s, con resultados específicos, replay, especificación inválida, clases ARX y adyacencias vacías, y rechazo efectivo de conexiones/procesos Java. [Artefactos](evidence/v021-native-tools-artifacts.json) y [fuentes](../sources/contracts-v021-native-tools.json).

La [respuesta oficial de Census](evidence/v021-census-public-metadata.json) del 15 de noviembre devolvió cinco tablas de metadatos, sin clave. Esto no certifica una consulta demográfica ni la disponibilidad futura del servicio.

El checkpoint `11b5a44` aprobó runtimes ([43675593741](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43675593741)), incluido `database021` con sockets Unix sin red, y servicios originales ([43675593745](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43675593745)). Verificación falló porque un gate conservaba el contador HTTP 102 anterior, aunque sus pruebas unitarias/Termux/SQLite pasaron. Los contadores de gates se actualizan junto con este nuevo inventario; su CI debe observarse por separado.

El checkpoint de 57 `e4283187b145e8639f29d23bafff8481c616b821` aprobó [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43677805478), [runtimes](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43677805475) y [servicios originales](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43677805490). No sustituye el CI del nuevo checkpoint.

`source021` pasó en 8.994 s con CUA, TinyTroupe, reglas NAP y Google Maps Scraper en el mismo producto, reinicio/replay, fallo del parser sin título y muestras de medias iguales. TinyTroupe usa NumPy 2.4.6/SciPy 1.15.3 fijados y `pip check`. CUA conserva archivos originales y licencia; solo cambia el import de tipos. TinyTroupe conserva su original y licencia; solo reemplaza el import del logger. Se verifica que esas sustituciones explican exactamente todos los bytes distintos. No se usan SDK ficticios ni módulos simulados. Maps compila `gmaps/entry.go` intacto con Go 1.26.11 y un puente propio de proyección. NAP compara campos exactos y devuelve solo IDs y campos discordantes; las instrucciones originales se verifican por Git SHA. [Evidencia de producto](evidence/v021-source021-local.json).

`media021` pasó en 50.116 s con Quarto y Auto-Editor originales, flujo conjunto, reinicio/replay, silencio PCM y texto que intenta incluir archivos/código/enlaces/HTML. Quarto recibe Markdown escapado y formato HTML minimal fijo; Deno deniega red y se rechaza contenido activo. Auto-Editor recibe WAV generado de 800–8000 amplitudes a 8000 Hz, PCM 16 bits; la cuantización se refleja en los niveles. No se aceptan archivos, comandos, filtros, formatos o URLs del llamante. Se fijan 2601 archivos de las distribuciones originales, incluidos binarios y licencias. `VERDUGO_MEDIA_ROOT` elige el perfil preparado por el administrador. [Artefactos](evidence/v021-media-artifacts.json) y [resultados](evidence/v021-media021-local.json). Estos ejecutables son Linux x86_64; no se presume compatibilidad Termux.

El checkpoint de 63, `8403d02405ea6a58f3e0080706bc3aa224e45513`, aprobó [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43679453741), [runtimes](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43679453649) y [servicios originales](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43679453654), incluidos source021 y media021. Su CI no sustituye la aceptación del nuevo checkpoint.

`images021` pasó en 6.639 s: CLI Microsandbox 0.7.15 original, producto y replay. La imagen Docker se genera solo con nombres fijos y textos suministrados; no ejecuta comandos de huésped. El digest y tamaño que devuelve `msb image inspect` deben coincidir con el archivo importado. HOME/XDG y la caché son privados y temporales. Este host no tiene `/dev/kvm`; eso impide afirmar ejecución de VM, pero no bloquea esta función de imágenes. [Artefactos](evidence/v021-images-artifacts.json), [producto](evidence/v021-images021-local.json) y [fuentes](../sources/contracts-v021-last-originals.json).

Landscape App pasó el producto/replay en 8.669 s y el caso de repositorio/fecha inválidos en 2.092 s. Se ejecutan validateLandscape.js, settings, actualTwitter, fatalErrors y yaml originales; reporter.js solo sustituye ambas rutas `/tmp/landscape.json` por `landscape-errors.json` en el directorio privado. La prueba verifica la adaptación byte por byte. Un preload propio bloquea red y procesos hijos, y el entorno no contiene claves de GitHub ni variables de notificación. Los textos del reporte original nunca se guardan en SQLite; solo recuentos y validez. [Resultado](evidence/v021-landscape-local.json).

El perfil `lastnode021` ejecuta el servidor Playwright MCP 0.0.85 con cliente SDK 1.32.2 y Chromium 158.0.8127.18 original. `document.snapshot` está registrado en el mismo Engine. El host local rechaza AF_UNIX y no pudo abrir Chromium; la herramienta original pasó en CI del commit df413d105604d5b7359948e337610c99c39c08a2. El fallo anterior era isolated:true con un contexto ya suministrado: la API original exige reutilizar ese contexto privado. No se sustituyó el servidor ni el navegador. El worker solo llama browser_snapshot, escapa títulos, encabezados y botones, bloquea peticiones de página y servicios worker, y cierra Chromium antes de devolver el resultado. El contenido original no llega a SQLite. La descarga automática desde cdn.playwright.dev devolvió HTML de sitio no disponible: se usa el ZIP original de Chrome for Testing en storage.googleapis.com, fijado por SHA-256.

El grupo network021 pasó localmente 20 pruebas en 46.106 s (17 omitidas por pertenecer a otros perfiles). Incluye ambos programas originales a través de Engine, composición y replay, una página inalcanzable y una respuesta HTTP 200 que contiene el marcador de ausencia. Los únicos destinos son 127.0.0.1 y un puerto efímero generado; Host y credenciales efímeras se comprueban en el servidor. Las salidas proyectadas omiten URLs, cuerpos y credenciales. El padre cierra conexiones y servidor antes de devolver éxito. CI habilita solo loopback dentro del namespace sin red externa.

La prueba inicial usó una compilación Node 24.22.1 distinta de la extraída del archivo oficial. El perfil final fija el SHA-256 e32e2d16081cf644f88392934288086e7662529d0d43277c34f7aad2207cfafb de ese archivo oficial; la aceptación del perfil exacto network021 pasó en CI de 3d7a2df (job 132713693238). Durante la repetición local el entorno se desconectó; no se atribuye éxito a esa repetición ni a una nueva suite conjunta de 67. La última composición conjunta observada sigue siendo la de 65 y 66 pasos, conservada en evidencia.

Microsandbox original pasó también en CI del checkpoint 5710826. Landscape App pasó sus pruebas originales en ese CI; el trabajo completo lastnode021 falló por la herramienta de Playwright MCP. Ese fallo se resolvió en df413d1 y el job 132715169636 aprobó las cuatro pruebas activas (20 descubiertas, 16 de otros perfiles omitidas) en 8.745 s. La aceptación posterior del adaptador ya registrado se exige en el commit vigente.

El perfil `closure021` prepara los cinco últimos programas originales (Microsandbox, Landscape, Playwright MCP, SiteOne y Sherlock) y exige su composición junto a los 26 contratos HTTP sintéticos en un mismo Engine/SQLite: 32 pasos contando la instantánea local. Reabre SQLite, prohíbe volver a llamar a workers o transportes en replay y comprueba que las entradas privadas no se persistan. Es una aceptación adicional a la composición previa de 65, no una afirmación de una nueva ejecución conjunta de 68 en el entorno local interrumpido. Cada perfil del resto de programas se vuelve a ejecutar en CI. Los artefactos y estados del workflow deben corresponder al commit que se evalúa.

El ZIP de Chromium se verifica por SHA-256 antes de extraerlo; su manifiesto de archivos se genera durante la preparación administrativa, y cada archivo vuelve a verificarse en planificación y ejecución. Un manifiesto cambiado invalida el perfil. No hay instalación dentro del motor. El runtime usa Node oficial y versiones npm exactas con integridad del lockfile; los binarios son Linux x86_64. [Contrato MCP fijado](../sources/contracts-v021-mcp.json).

La integración final del commit `558e12177fd5549f65b878d8f94cebb25243d12f` aprobó [lastnode021](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43682669882/job/132716458689) y [closure021](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43682669882/job/132716458688). Incluyen MCP real por Engine, rechazo de manifiesto de navegador alterado, marcado HTML tratado como texto, privacidad y replay de los 32 pasos del flujo final. En ese commit la verificación global detectó una referencia checkout alterada y dos contadores históricos que aún esperaban un pendiente; se corrigen aquí sin omitir pruebas. La aprobación global debe comprobarse en los tres workflows del commit final, no deducirse de estos dos jobs.
