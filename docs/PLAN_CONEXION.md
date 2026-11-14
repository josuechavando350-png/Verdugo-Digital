# Verdugo Digital — Plan para conectar lo que falta

Fecha: 14 de noviembre de 2026. Versión del motor: 0.20.0.

| Estado | Cuántas |
|---|---|
| conectado | 156 |
| pieza_de_construccion | 56 |
| pendiente | 88 |
| excluido | 22 |
| **Total** | 322 |

**Pendientes: 88**, conservando las cuatro tandas originales (27, 21, 27 y 13). Las 56 *piezas de construcción* (Next.js, Tailwind, shadcn, Expo…)
no se conectan al motor: se usan al construir la plataforma (fase aparte). Las 22 excluidas por licencia no se tocan.

El estado de cada pieza lo calcula el código: `python -m verdugo connections`. Este plan en formato
de máquina está en `docs/plan_conexion.json`.

## Continuación v0.17: cuatro contratos implementados, no cuatro instalaciones

Se continúa el plan de Claude del commit `35516f830cba1e0dbb06b91f44357128440fc832`.
Se conservan sus reglas, orden y numeración originales: la tanda 1 tiene ahora
46 pendientes y las otras tandas mantienen 50, 50 y 35. No se renumeran las piezas
para no perder su referencia histórica.

- `openrefine`: recuento de proyectos, exclusivamente detrás de un proxy autenticador revisado.
- `steel-browser`: recuento de sesiones por estado, con el mismo requisito de proxy.
- `crawl4ai`: inventario de acciones declarativas disponibles; no ejecuta rastreo ni hooks. Requiere proxy.
- `fides`: recuento de políticas DSR, primera página y token OAuth nativo de lectura.

Pasaron pruebas de contrato y HTTP local con respuestas sintéticas; **no se han
instalado ni verificado esos proveedores reales**. Los cuatro siguen deshabilitados
hasta que el operador revise versión, licencia y credenciales. Los proxies no se
crearon y su existencia no se presume. La tanda completa no está terminada.
[Contratos, fuentes y límites](TANDA1_V017.md).

## Continuación v0.18: inventario y disponibilidad acotados

Se parte de `da34f47b6bc6116e553f08801e281f1e695dcc8c` (PR #16), sin
alterar la política de licencias ni los 322 registros. Se completan dos contratos
más; la tanda 1 conserva **44 pendientes** y las demás mantienen 50, 50 y 35.

- `uptime-kuma` (`monitors.summary`): se corrige explícitamente la nota anterior
  «solo expone /metrics». El **mismo commit fijado** sí contiene `GET /api/monitors`,
  con `requireApiKey`, Bearer y la opción `API and MCP` habilitada. Es una API Alpha;
  no se presume disponible en versiones anteriores. Se guardan solo recuentos.
- `gotenberg` (`health.summary`): `GET /health` omite la autenticación nativa incluso
  si se habilita Basic/OIDC. Se exige un proxy Bearer autenticador revisado; no se
  creó ese proxy y una marca de configuración no demuestra que exista.

Los números y notas originales retirados de la lista de pendientes se conservan
como `implemented_v018`/`nota_previa` en el JSON. No se renumera el trabajo restante.
Las pruebas locales de contratos no certifican servidores instalados, captación,
monitores saludables ni conversión documental. [Alcance](TANDA1_V018.md).

## Continuación v0.19: operación conjunta y cuatro contratos

Base exacta: `088c759033fd52e2ece9f6cb0d23590bd378a160` (PR #17).
`product-status` reúne las 322 piezas y el estado comercial local.
`product-run` usa el mismo workflow/Engine para 33 consultas con proyección segura,
más una instantánea de métricas locales. No suma entidades distintas ni convierte
monitores, repositorios o servidores en ingresos. Distingue observación nueva de
replay, conserva la hora original y muestra pasos detenidos y no iniciados.

Cuatro operaciones más de la tanda 1: Apache Answer (notificaciones), Caddy
(servidores HTTP configurados), SeaweedFS (topología) y Dagster (repositorios por
GraphQL fijo de lectura). Los tres últimos exigen proxy Bearer revisado. La lista
retirada y las notas originales están en `implemented_v019`; quedan **40, 50, 50 y 35**
pendientes. Los 300 permitidos, 22 excluidos y 56 componentes se conservan.

36 pruebas nuevas: contratos, transporte local, flujo de 33 respuestas sintéticas,
reinicio, fallo parcial, concurrencia, aislamiento y CLI/MCP. La aceptación de
Caddy original se ejecuta aparte en `real-services.yml`, compilando el commit del
contrato; no atribuir ese resultado a Answer, SeaweedFS, Dagster, Kuma o Gotenberg.
[Uso, contratos y límites](PRODUCTO_V019.md).

## Continuación v0.20: 87 operaciones adicionales

Base exacta: `b98f5cc8edd1543b08188c36459f01154ef00c48` (PR #18).
76 bibliotecas originales, dos consultas de datos originales fijados y nueve
contratos HTTP se incorporan al mismo producto. `product-run` admite análisis
locales, referencias entre resultados y reanudación persistida. Las dependencias
incompatibles se aíslan en entornos Python; Engine y SQLite siguen siendo únicos.

El estado vigente pasa de 69 a **156 conectadas** y de 175 a **88 pendientes**.
Las entradas retiradas se conservan en `implemented_v020`; los números de las
cuatro tandas históricas no se renumeran. Las 56 piezas de construcción y 22
excluidas se conservan. Conectado significa una operación delimitada implementada,
no instalación productiva ni cobertura completa del programa original.
[Operaciones, fuentes, pruebas y límites](AMPLIACION_V020.md).

## Reglas para cada conector (obligatorias)

1. Leer `AGENTS.md` y `README.md`. Correr `python -m unittest discover -s tests -v` antes y después.
2. La ruta, la autenticación y la forma de respuesta salen del **código fuente u OpenAPI en el commit fijado** de `sources/parts` (o de la documentación oficial si el código no la trae, citándola). Nunca de memoria.
3. Solo lectura y acotado: `GET` (o un POST de lectura fijo en código), una página, parámetros fijos. Nada de URL, método, consulta, token ni tenant desde `params`.
4. Guardar solo recuentos o estados. Nunca correos, nombres, teléfonos, IPs, montos de clientes ni el payload completo.
5. Sin servicios de pago. Si un servicio solo existe en la nube de pago, se marca bloqueado.
6. Sin excepciones de licencia en nombre de Josue. Las 22 excluidas siguen excluidas.
7. Si no se puede verificar o no aplica, **no se inventa**: queda pendiente con el motivo escrito en la nota.
8. Pruebas por conector: contrato (ruta, encabezados, consulta), proyección sin datos privados, esquema inválido que falla, parámetros prohibidos y, para HTTP, servidor loopback.
9. Actualizar los conteos en las pruebas y en `.github/workflows/verify.yml`, `README.md` y `docs/CONECTORES_V015.md`.
10. No tocar la cuenta ni los despliegues de Vercel ni proyectos de clientes. Las librerías `vercel/next.js` y `vercel/ai` sí se pueden usar.
11. Una rama y un PR por tanda. El CI de GitHub tiene que pasar en verde antes de pedir la fusión.

## Definición de terminado por tanda

- Cada pieza de la tanda queda **conectada** (adaptador o receta implementada y probada) o **pendiente con motivo**.
- `python -m verdugo connections` refleja el nuevo número de conectadas.
- Los tres workflows de CI y todos sus trabajos en verde. Ninguna se marca como probada contra un servidor real si no se probó.

## Tanda 1 — servicios que traen clientes, MCP, protocolo y datos (27)

| # | Pieza | Repositorio @ commit | Licencia | Tipo | Qué hacer / nota |
|---|---|---|---|---|---|
| 3 | `krayin-crm` | [krayin/laravel-crm@ed6deebfcb](https://github.com/krayin/laravel-crm/tree/ed6deebfcb8c616eaf352c893a10a6d8e666fc6e) | MIT | servicio | Adaptador HTTP. Su paquete REST (krayin/rest-api) no tiene licencia: no usarlo. Bloqueado salvo que publiquen licencia. |
| 4 | `anubis` | [TecharoHQ/anubis@f197f9a623](https://github.com/TecharoHQ/anubis/tree/f197f9a6235d255000c7b654ac478354a6e4bd02) | MIT | servicio | Adaptador HTTP. Proxy anti-bots; revisar si tiene endpoint de métricas o estado con autenticación. |
| 6 | `webmention-io` | [aaronpk/webmention.io@9183deed82](https://github.com/aaronpk/webmention.io/tree/9183deed829c2399e6cd7f594ab8f1d84492e86b) | BSD (declarada en README) | servicio | Adaptador HTTP. El token va en la URL: prohibido. Bloqueado salvo soporte por encabezado. |
| 7 | `letta` | [letta-ai/letta@8816d3a851](https://github.com/letta-ai/letta/tree/8816d3a8516893bfdc0fa14bfb1235226012e295) | Apache-2.0 | servicio | Adaptador HTTP. En el commit fijado el repo ya no trae el código del servidor. Ubicar el repo oficial del servidor y volver a fijarlo, o marcar no_aplica. |
| 8 | `microsandbox` | [microsandbox/microsandbox@28bdced502](https://github.com/microsandbox/microsandbox/tree/28bdced502513f46b2372dade590ba7e91466242) | Apache-2.0 | servicio | Adaptador HTTP. Su API es JSON-RPC por POST. Requiere un contrato POST de solo lectura fijo en código (mismo patrón que Plausible en marketing_reads). |
| 9 | `openhands` | [All-Hands-AI/OpenHands@685eb42ded](https://github.com/All-Hands-AI/OpenHands/tree/685eb42ded117ba0321aa8c3019e6677e5474317) | MIT | servicio | Adaptador HTTP.  |
| 11 | `huginn` | [huginn/huginn@639c050b2b](https://github.com/huginn/huginn/tree/639c050b2bf4e14ef9983012af99dfc1dc68b334) | MIT | servicio | Adaptador HTTP. No tiene API JSON de lectura. Bloqueado. |
| 16 | `debezium` | [debezium/debezium@a4c282ea70](https://github.com/debezium/debezium/tree/a4c282ea70d3f913df699464f3e42f9ddb7eb03e) | Apache-2.0 | servicio | Adaptador HTTP.  |
| 21 | `valkey` | [valkey-io/valkey@c98c0e2e6c](https://github.com/valkey-io/valkey/tree/c98c0e2e6c271a24c829d17b2ed94d64c576c33f) | BSD-3-Clause | servicio | Adaptador HTTP. Protocolo RESP, no HTTP. Receta local con cliente oficial y comando fijo (INFO). |
| 22 | `tusd` | [tus/tusd@cec3998089](https://github.com/tus/tusd/tree/cec39980890809a9e7202872ec32f736f3b4a3f5) | MIT | servicio | Adaptador HTTP. Servidor de subidas sin API de lectura útil. Probable no_aplica. |
| 25 | `postal` | [postalserver/postal@d96eddbade](https://github.com/postalserver/postal/tree/d96eddbadeda600595d6247486f9ceb8e99cbc15) | MIT | servicio | Adaptador HTTP. Su API es de envíos (POST). Sin lectura: bloqueado. |
| 27 | `google-ads` | [googleads/google-ads-python@f253b400dc](https://github.com/googleads/google-ads-python/tree/f253b400dc5924b731fcb42dbcd99e485200581e) | Apache-2.0 | servicio | Adaptador HTTP. La librería oficial solo trae gRPC. Tomar la ruta REST GET customers:listAccessibleCustomers de la documentación oficial (versión v26 fijada). Necesita OAuth y developer-token (segundo secreto por variable VERDUGO_*). |
| 28 | `meta-ads` | [meta/facebook-python-business-sdk@b08e5c1d36](https://github.com/meta/facebook-python-business-sdk/tree/b08e5c1d36a2adad3c4ede6578654c8eaca5f225) | LicenseRef-Meta-Platform | servicio | Adaptador HTTP. El SDK manda access_token en la URL: prohibido. Solo conectar si la documentación oficial de Graph API confirma el encabezado Authorization: Bearer. |
| 30 | `postgres` | [postgres/postgres@8d87367b39](https://github.com/postgres/postgres/tree/8d87367b39e44b0913ca585c733795cc2d30bff1) | PostgreSQL | servicio | Adaptador HTTP. No es HTTP. Leer vía PostgREST (componente) o con un driver de solo lectura en receta local. |
| 31 | `livekit` | [livekit/agents@59753ba7d7](https://github.com/livekit/agents/tree/59753ba7d759621ffb256b8023ebf2ddf70ffa9a) | Apache-2.0 | servicio | Adaptador HTTP. API Twirp por POST con JWT firmado con api_key/secret. Requiere firma local revisada. |
| 32 | `temporal` | [temporalio/temporal@03ecd1d228](https://github.com/temporalio/temporal/tree/03ecd1d228d2b8d9d433da55785afc9aeeead918) | MIT | servicio | Adaptador HTTP. Verificar la API HTTP (grpc-gateway) /api/v1/namespaces en el commit fijado. |
| 35 | `otel-collector` | [open-telemetry/opentelemetry-collector@e366bb7fb4](https://github.com/open-telemetry/opentelemetry-collector/tree/e366bb7fb49a67fd117332fff93795a0050744ff) | Apache-2.0 | servicio | Adaptador HTTP.  |
| 36 | `mcp-gsc` | [AminForou/mcp-gsc@45291df024](https://github.com/AminForou/mcp-gsc/tree/45291df024c7873b2042c83d7add70ced7bb621f) | MIT | mcp | Registro MCP.  |
| 37 | `opengmb` | [synectus/OpenGMB@8f399472e9](https://github.com/synectus/OpenGMB/tree/8f399472e9d484cfcad77eef33b0da341e469577) | MIT | mcp | Registro MCP.  |
| 38 | `nlweb` | [microsoft/NLWeb@b423f15d9a](https://github.com/microsoft/NLWeb/tree/b423f15d9aeaa023ce75993ac9deed2354597043) | MIT | mcp | Registro MCP.  |
| 41 | `local-seo-skills` | [garrettjsmith/localseoskills@c3b7a25b7d](https://github.com/garrettjsmith/localseoskills/tree/c3b7a25b7d5cc370752d74cfea240ccf992a24db) | MIT | mcp | Registro MCP.  |
| 42 | `a2a` | [a2aproject/A2A@4d7cda4b17](https://github.com/a2aproject/A2A/tree/4d7cda4b1754ed410e41bf3be7ad9ebc62afe3d3) | Apache-2.0 | protocolo | SDK A2A.  |
| 43 | `playwright-mcp` | [microsoft/playwright-mcp@78eca85361](https://github.com/microsoft/playwright-mcp/tree/78eca85361efb545a4c0f59b6140aef0721c5412) | Apache-2.0 | mcp | Registro MCP.  |
| 44 | `claude-skills-c-level` | [alirezarezvani/claude-skills@08cd8a9fc8](https://github.com/alirezarezvani/claude-skills/tree/08cd8a9fc86cc370e2c0d448e8171fbcfdbc5a30) | MIT | mcp | Registro MCP.  |
| 45 | `openprospector` | [clawnify/OpenProspector@dad0e778ff](https://github.com/clawnify/OpenProspector/tree/dad0e778ff4e1438b69574ff9cbb7663a3bda6e6) | MIT | biblioteca | Receta local.  |
| 46 | `openseo` | [duckduckdeploy/openseo@12b5254005](https://github.com/duckduckdeploy/openseo/tree/12b525400539f980668d088ff7154236a2376e88) | MIT | biblioteca | Receta local.  |
| 48 | `kingfisher-collect` | [open-contracting/kingfisher-collect@865bbb20ff](https://github.com/open-contracting/kingfisher-collect/tree/865bbb20ff4e6495bd2aba08bef5f2a0a1a648f6) | BSD-3-Clause | biblioteca | Receta local.  |

## Tanda 2 — bibliotecas (marketing, autoridad, agentes, motor de datos) (21)

| # | Pieza | Repositorio @ commit | Licencia | Tipo | Qué hacer / nota |
|---|---|---|---|---|---|
| 3 | `geo-lint` | [IJONIS/geo-lint@b2d79319d1](https://github.com/IJONIS/geo-lint/tree/b2d79319d1d0d4d4fc5d6abbc4ce5156afc5d14b) | MIT | biblioteca | Receta local.  |
| 4 | `autogeo` | [cxcscmu/AutoGEO@49456df236](https://github.com/cxcscmu/AutoGEO/tree/49456df236774ea24087c44f45e9e52005b8e6a4) | MIT | biblioteca | Receta local.  |
| 5 | `site-md` | [yazinsai/site-md@c5c31bc781](https://github.com/yazinsai/site-md/tree/c5c31bc781d06f83a81d30a284f0df3aa2ffbe32) | MIT | biblioteca | Receta local.  |
| 6 | `seo-graph` | [jdevalk/seo-graph@c33eb1e120](https://github.com/jdevalk/seo-graph/tree/c33eb1e120c620970042e28f1332fc90c30125e6) | MIT | biblioteca | Receta local.  |
| 7 | `structured-data-validator` | [adobe/structured-data-validator@6918b52651](https://github.com/adobe/structured-data-validator/tree/6918b52651d6f4c5dae612859e2e395de5a1910e) | Apache-2.0 | biblioteca | Receta local.  |
| 11 | `cc-webgraph` | [commoncrawl/cc-webgraph@8a3a34e2f3](https://github.com/commoncrawl/cc-webgraph/tree/8a3a34e2f3bc16b865ee234eab83a4917086b814) | Apache-2.0 | biblioteca | Receta local.  |
| 12 | `trendspyg` | [flack0x/trendspyg@9f07b2573e](https://github.com/flack0x/trendspyg/tree/9f07b2573e7287df85df9202da206569024723e9) | MIT | biblioteca | Receta local.  |
| 14 | `newsjack` | [elvisun/newsjack@c2df3a0168](https://github.com/elvisun/newsjack/tree/c2df3a0168083d620b9b36518aeca16a4eb72296) | MIT | biblioteca | Receta local.  |
| 15 | `gdeltdoc` | [alex9smith/gdelt-doc-api@41220163fb](https://github.com/alex9smith/gdelt-doc-api/tree/41220163fbab99982e4dca3a05d25a95b49896d7) | MIT | biblioteca | Receta local.  |
| 17 | `python-podcastindex` | [piqosoft/python-podcastindex@63fdb84b76](https://github.com/piqosoft/python-podcastindex/tree/63fdb84b76b5d65c99e9c92428af55cc51aff04e) | MIT | biblioteca | Receta local.  |
| 18 | `praw` | [praw-dev/praw@4590cb5b0a](https://github.com/praw-dev/praw/tree/4590cb5b0ad2f9afbab983d60d792fc3c74d1f45) | BSD-2-Clause | biblioteca | Receta local.  |
| 19 | `youtube-comment-downloader` | [egbertbouman/youtube-comment-downloader@3f557bc802](https://github.com/egbertbouman/youtube-comment-downloader/tree/3f557bc8023d9e3ab9edda93bcd516ca2b33d3c1) | MIT | biblioteca | Receta local.  |
| 20 | `people-also-ask` | [labsonmars/people_also_ask@21db28fb5a](https://github.com/labsonmars/people_also_ask/tree/21db28fb5a75d233bf18db381fab538791eee495) | MIT | biblioteca | Receta local.  |
| 21 | `c2pa` | [contentauth/c2pa-rs@0e92435c6d](https://github.com/contentauth/c2pa-rs/tree/0e92435c6d621c02c9bde2a8d82346295ed1f509) | Apache-2.0 OR MIT | biblioteca | Receta local.  |
| 33 | `graphiti` | [getzep/graphiti@3ed0252749](https://github.com/getzep/graphiti/tree/3ed02527499d4eb3b2eb133d716898dc89d7cc99) | Apache-2.0 | biblioteca | Receta local.  |
| 34 | `browser-use` | [browser-use/browser-use@480d0bd508](https://github.com/browser-use/browser-use/tree/480d0bd508ce10dcf27a4716f2f87355a08e8372) | MIT | biblioteca | Receta local.  |
| 37 | `mcp-agent` | [lastmile-ai/mcp-agent@f62d849350](https://github.com/lastmile-ai/mcp-agent/tree/f62d849350816588b1c6294e7914bbe4d8b84072) | Apache-2.0 | biblioteca | Receta local.  |
| 39 | `nemo-guardrails` | [NVIDIA/NeMo-Guardrails@5d7f4c1ca6](https://github.com/NVIDIA/NeMo-Guardrails/tree/5d7f4c1ca62fb6155066e6c581379d1a5ec11338) | Apache-2.0 | biblioteca | Receta local.  |
| 42 | `storm` | [stanford-oval/storm@fb951af774](https://github.com/stanford-oval/storm/tree/fb951af7744dab086e34962e9bc6fe878e145f83) | MIT | biblioteca | Receta local.  |
| 43 | `humanlayer` | [humanlayer/humanlayer@b7ad8e1d38](https://github.com/humanlayer/humanlayer/tree/b7ad8e1d383ff0f5fbec7bdc30425e4a59d5f789) | Apache-2.0 | biblioteca | Receta local.  |
| 44 | `cua` | [trycua/cua@c372e5fb2b](https://github.com/trycua/cua/tree/c372e5fb2bae944974e903fbf117c61f4ced696e) | MIT | biblioteca | Receta local.  |

## Tanda 3 — programas de línea de comandos (requiere runner nuevo) y bibliotecas (27)

| # | Pieza | Repositorio @ commit | Licencia | Tipo | Qué hacer / nota |
|---|---|---|---|---|---|
| 1 | `siteone-crawler` | [janreges/siteone-crawler@f3d967b190](https://github.com/janreges/siteone-crawler/tree/f3d967b190a77ff5f816b7ddab74c1a778d9dbaf) | MIT | cli | Receta CLI.  |
| 2 | `goaccess` | [allinurl/goaccess@6e890b584b](https://github.com/allinurl/goaccess/tree/6e890b584b8b36c445aa37dea83d7d5519d5fc46) | MIT | cli | Receta CLI.  |
| 3 | `sherlock` | [sherlock-project/sherlock@c588d7c8b4](https://github.com/sherlock-project/sherlock/tree/c588d7c8b476df9f9c84912a05d1430fb8cdcdae) | MIT | cli | Receta CLI.  |
| 4 | `google-maps-scraper` | [gosom/google-maps-scraper@e0c1d501e4](https://github.com/gosom/google-maps-scraper/tree/e0c1d501e49cdcd5c6b2cecd2a032831f6ee9ba8) | MIT | cli | Receta CLI.  |
| 5 | `dnstwist` | [elceef/dnstwist@341395377f](https://github.com/elceef/dnstwist/tree/341395377f40761fe4152f43fd18eea757b6069a) | Apache-2.0 | cli | Receta CLI.  |
| 6 | `vale` | [errata-ai/vale@4ce91ef208](https://github.com/errata-ai/vale/tree/4ce91ef208b37f9ac2894766e8cd7b33ffe3baed) | MIT | cli | Receta CLI.  |
| 7 | `quarto` | [quarto-dev/quarto-cli@1782b5b309](https://github.com/quarto-dev/quarto-cli/tree/1782b5b3099e8e4dd62cf7bac590d3bad2072c56) | MIT | cli | Receta CLI.  |
| 8 | `auto-editor` | [WyattBlue/auto-editor@2bbdcd95bc](https://github.com/WyattBlue/auto-editor/tree/2bbdcd95bc221254e4e6e00eb4c827b06ae93f71) | Unlicense | cli | Receta CLI.  |
| 9 | `slidev` | [slidevjs/slidev@437f139ccd](https://github.com/slidevjs/slidev/tree/437f139ccd4c8482a193b217922e7800a5b3baec) | MIT | cli | Receta CLI.  |
| 10 | `dvc` | [iterative/dvc@b59add99ee](https://github.com/iterative/dvc/tree/b59add99ee667f2b352cc1be337619f965fe3fea) | Apache-2.0 | cli | Receta CLI.  |
| 11 | `landscape-app` | [cncf/landscapeapp@a882d0675b](https://github.com/cncf/landscapeapp/tree/a882d0675b2cd9ace3fa158f6d8df3b65a5a82cf) | Apache-2.0 | cli | Receta CLI.  |
| 12 | `log4brains` | [thomvaill/log4brains@17e32021a8](https://github.com/thomvaill/log4brains/tree/17e32021a8c5130386f17e921d4efa6da7709a66) | Apache-2.0 | cli | Receta CLI.  |
| 13 | `openapi-generator` | [OpenAPITools/openapi-generator@1d942536cd](https://github.com/OpenAPITools/openapi-generator/tree/1d942536cd430bd303076e0eef28325cc6e965fe) | Apache-2.0 | cli | Receta CLI.  |
| 14 | `lighthouse` | [GoogleChrome/lighthouse@5313024aa0](https://github.com/GoogleChrome/lighthouse/tree/5313024aa05786138dfd38c6740ef354e20c3f92) | Apache-2.0 | cli | Receta CLI.  |
| 15 | `promptfoo` | [promptfoo/promptfoo@e5ca12a10b](https://github.com/promptfoo/promptfoo/tree/e5ca12a10bf4e28d8598bc800f3e4f2ad0053b2d) | MIT | cli | Receta CLI.  |
| 16 | `dbt` | [dbt-labs/dbt@3a3c73e46a](https://github.com/dbt-labs/dbt/tree/3a3c73e46acb63bf09dbcb53ebaea1d7efdffe2e) | Apache-2.0 | cli | Receta CLI.  |
| 17 | `sops` | [getsops/sops@9aa10f12bc](https://github.com/getsops/sops/tree/9aa10f12bcd82400b7eb73331dd7a87a93bb17f7) | MPL-2.0 | cli | Receta CLI. MPL-2.0: si modificas sus archivos, esos archivos se comparten. |
| 18 | `grype` | [anchore/grype@cd1f23eb50](https://github.com/anchore/grype/tree/cd1f23eb50dfb52647090158f453c7359172591f) | Apache-2.0 | cli | Receta CLI.  |
| 19 | `syft` | [anchore/syft@a0c0d3890a](https://github.com/anchore/syft/tree/a0c0d3890a9d79421c403e8fcadec50a2e55bf21) | Apache-2.0 | cli | Receta CLI.  |
| 20 | `gitleaks` | [gitleaks/gitleaks@5f6ec56cfa](https://github.com/gitleaks/gitleaks/tree/5f6ec56cfa6f8c67648d863582c7ae2f206d5c1c) | MIT | cli | Receta CLI.  |
| 21 | `restic` | [restic/restic@c734245fd3](https://github.com/restic/restic/tree/c734245fd3ae9bcac8ab3aaafb4482d4b5d0ae92) | BSD-2-Clause | cli | Receta CLI.  |
| 25 | `apache-age` | [apache/age@8c7e44fd2a](https://github.com/apache/age/tree/8c7e44fd2a525dedfd3d4e8168921442eb4fce2f) | Apache-2.0 | biblioteca | Receta local.  |
| 28 | `tfcausalimpact` | [WillianFuks/tfcausalimpact@99bd5fb866](https://github.com/WillianFuks/tfcausalimpact/tree/99bd5fb866acb352daf1b58c17d8f711d0e1a9ec) | Apache-2.0 | biblioteca | Receta local.  |
| 33 | `chronos` | [amazon-science/chronos-forecasting@1224fafa91](https://github.com/amazon-science/chronos-forecasting/tree/1224fafa91e1ecd6674f5204066b159e40b5e4a1) | Apache-2.0 | biblioteca | Receta local.  |
| 38 | `gliner` | [urchade/GLiNER@beb41b3839](https://github.com/urchade/GLiNER/tree/beb41b3839267952d0f063c04dd6236e9fd93a38) | Apache-2.0 | biblioteca | Receta local.  |
| 39 | `arx` | [arx-deidentifier/arx@4e0a5f5340](https://github.com/arx-deidentifier/arx/tree/4e0a5f5340fe9a58c44b34c2f9acd2d68f1dad5f) | Apache-2.0 | biblioteca | Receta local.  |
| 46 | `cognee` | [topoteretes/cognee@4053f6cc55](https://github.com/topoteretes/cognee/tree/4053f6cc5536757f26a3665eed95c50088e6dc0b) | Apache-2.0 | biblioteca | Receta local.  |

## Tanda 4 — bibliotecas restantes (13)

| # | Pieza | Repositorio @ commit | Licencia | Tipo | Qué hacer / nota |
|---|---|---|---|---|---|
| 2 | `tinytroupe` | [microsoft/TinyTroupe@7ce8be378a](https://github.com/microsoft/TinyTroupe/tree/7ce8be378a37ee73f9745d6781452712318afa04) | MIT | biblioteca | Receta local.  |
| 3 | `gpt-researcher` | [assafelovic/gpt-researcher@ddd4db3620](https://github.com/assafelovic/gpt-researcher/tree/ddd4db36208d9c8e49f3b2436efda97baecb5433) | Apache-2.0 | biblioteca | Receta local.  |
| 5 | `datosmex` | [andreslomeliv/DatosMex@4179265209](https://github.com/andreslomeliv/DatosMex/tree/4179265209ca8345cc2de533f82612a6ca45314f) | MIT | biblioteca | Receta local. MIT en las subcarpetas BANXICOpy e INEGIpy. |
| 6 | `wbgapi` | [tgherzog/wbgapi@4d0d2c925a](https://github.com/tgherzog/wbgapi/tree/4d0d2c925a8dac359df5a2d9e82001ff6feeecda) | MIT | biblioteca | Receta local.  |
| 7 | `census` | [datamade/census@3da5a10681](https://github.com/datamade/census/tree/3da5a1068164c27f6e83815f5d28ec300e184fdf) | BSD-3-Clause | biblioteca | Receta local.  |
| 8 | `comtradeapicall` | [uncomtrade/comtradeapicall@d8b1958898](https://github.com/uncomtrade/comtradeapicall/tree/d8b19588986405df8c3c94062bd73fd08b9110cd) | MIT | biblioteca | Receta local.  |
| 10 | `openbb` | [OpenBB-finance/OpenBB@e43353a828](https://github.com/OpenBB-finance/OpenBB/tree/e43353a82815ff9ba56ad1b7ad47c32729dcf314) | Apache-2.0 | biblioteca | Receta local.  |
| 12 | `jobspy` | [speedyapply/JobSpy@68b88d6909](https://github.com/speedyapply/JobSpy/tree/68b88d6909a2342ad75fbb945c4204a3a7ed6665) | MIT | biblioteca | Receta local.  |
| 15 | `pricesensitivitymeter` | [max-alletsee/pricesensitivitymeter@8188de1e95](https://github.com/max-alletsee/pricesensitivitymeter/tree/8188de1e95fa0f407073677f6f88baec2f43c8d4) | MIT | biblioteca | Receta local. Licencia MIT de R (archivo corto con año y titular). |
| 26 | `vanna` | [vanna-ai/vanna@365d0617c1](https://github.com/vanna-ai/vanna/tree/365d0617c1a4567ffee1b19b40c27feb4206bfcf) | MIT | biblioteca | Receta local.  |
| 30 | `pgvector` | [pgvector/pgvector@66accb3af6](https://github.com/pgvector/pgvector/tree/66accb3af6705ea9975a33f6704f1cde50d99447) | PostgreSQL | biblioteca | Receta local.  |
| 32 | `robyn` | [facebookexperimental/Robyn@aab4226ed5](https://github.com/facebookexperimental/Robyn/tree/aab4226ed5e40196cdbd82ff7fbbff55e91e1f58) | MIT | biblioteca | Receta local.  |
| 33 | `meridian` | [google/meridian@f4ca39d406](https://github.com/google/meridian/tree/f4ca39d406e1a86bd13d65fdf14166268044fd2d) | Apache-2.0 | biblioteca | Receta local.  |

## Cómo se conecta cada tipo

- **servicio**: Adaptador HTTP GET acotado en verdugo/service_reads.py: ruta, autenticación y forma de respuesta tomadas del código u OpenAPI en el commit fijado; proyección a recuentos; pruebas de contrato y loopback.
- **biblioteca**: Receta local en verdugo/local_extended.py (patrón v0.10): una función acotada, datos sintéticos, versión exacta en requirements/runtime*.txt con constraints generados por pip en CI y prueba real en tests_runtime.
- **cli**: Receta de proceso externo con binario en lista blanca y argumentos fijos, sin shell, con límite de tiempo. Requiere crear primero un runner de CLI acotado (no existe todavía).
- **mcp**: Registro como servidor MCP para agentes (configuración, no ejecución desde el motor) con versión fijada y permisos mínimos.
- **protocolo**: Implementar con su SDK oficial (a2a-python) como receta local.
- **datos**: Descargar fijado por commit en CI y leer localmente; nunca descargar en tiempo de ejecución.

## Fase aparte: la plataforma

Las 56 piezas de construcción se conectan programando la plataforma de Verdugo (panel web y app móvil)
que use el motor por su API/MCP. Esa fase se planea cuando las tandas de conectores avancen.

