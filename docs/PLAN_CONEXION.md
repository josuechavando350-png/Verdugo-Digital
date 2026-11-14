# Verdugo Digital — Plan para conectar lo que falta

Fecha: 14 de noviembre de 2026. Versión del motor: 0.16.0.

| Estado | Cuántas |
|---|---|
| conectado | 59 |
| pieza_de_construccion | 56 |
| pendiente | 185 |
| excluido | 22 |
| **Total** | 322 |

**Pendientes: 185**, en 4 tandas de hasta 50. Las 56 *piezas de construcción* (Next.js, Tailwind, shadcn, Expo…)
no se conectan al motor: se usan al construir la plataforma (fase aparte). Las 22 excluidas por licencia no se tocan.

El estado de cada pieza lo calcula el código: `python -m verdugo connections`. Este plan en formato
de máquina está en `docs/plan_conexion.json`.

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
- Las 5 revisiones del CI en verde. Ninguna se marca como probada contra un servidor real si no se probó.

## Tanda 1 — servicios que traen clientes, MCP, protocolo y datos (50)

| # | Pieza | Repositorio @ commit | Licencia | Tipo | Qué hacer / nota |
|---|---|---|---|---|---|
| 1 | `openrefine` | [OpenRefine/OpenRefine@d97abdabd4](https://github.com/OpenRefine/OpenRefine/tree/d97abdabd4c172ddba3581a9259307c7f2b86b44) | BSD-3-Clause | servicio | Adaptador HTTP. API sin autenticación (solo CSRF en POST). Solo tras proxy con token. |
| 2 | `uptime-kuma` | [louislam/uptime-kuma@4f6661cfa8](https://github.com/louislam/uptime-kuma/tree/4f6661cfa83a06be0353d5536ef3d9ee0064f534) | MIT | servicio | Adaptador HTTP. Solo expone /metrics en texto Prometheus. Leerlo a través de Prometheus (ya conectado) o con un parser de texto acotado. |
| 3 | `krayin-crm` | [krayin/laravel-crm@ed6deebfcb](https://github.com/krayin/laravel-crm/tree/ed6deebfcb8c616eaf352c893a10a6d8e666fc6e) | MIT | servicio | Adaptador HTTP. Su paquete REST (krayin/rest-api) no tiene licencia: no usarlo. Bloqueado salvo que publiquen licencia. |
| 4 | `anubis` | [TecharoHQ/anubis@f197f9a623](https://github.com/TecharoHQ/anubis/tree/f197f9a6235d255000c7b654ac478354a6e4bd02) | MIT | servicio | Adaptador HTTP. Proxy anti-bots; revisar si tiene endpoint de métricas o estado con autenticación. |
| 5 | `apache-answer` | [apache/answer@6744295fa8](https://github.com/apache/answer/tree/6744295fa888e0621fc9f9a8ace04f1a4daf8554) | Apache-2.0 | servicio | Adaptador HTTP.  |
| 6 | `webmention-io` | [aaronpk/webmention.io@9183deed82](https://github.com/aaronpk/webmention.io/tree/9183deed829c2399e6cd7f594ab8f1d84492e86b) | BSD (declarada en README) | servicio | Adaptador HTTP. El token va en la URL: prohibido. Bloqueado salvo soporte por encabezado. |
| 7 | `letta` | [letta-ai/letta@8816d3a851](https://github.com/letta-ai/letta/tree/8816d3a8516893bfdc0fa14bfb1235226012e295) | Apache-2.0 | servicio | Adaptador HTTP. En el commit fijado el repo ya no trae el código del servidor. Ubicar el repo oficial del servidor y volver a fijarlo, o marcar no_aplica. |
| 8 | `microsandbox` | [microsandbox/microsandbox@28bdced502](https://github.com/microsandbox/microsandbox/tree/28bdced502513f46b2372dade590ba7e91466242) | Apache-2.0 | servicio | Adaptador HTTP. Su API es JSON-RPC por POST. Requiere un contrato POST de solo lectura fijo en código (mismo patrón que Plausible en marketing_reads). |
| 9 | `openhands` | [All-Hands-AI/OpenHands@685eb42ded](https://github.com/All-Hands-AI/OpenHands/tree/685eb42ded117ba0321aa8c3019e6677e5474317) | MIT | servicio | Adaptador HTTP.  |
| 10 | `magentic-ui` | [microsoft/magentic-ui@d3c9d13c39](https://github.com/microsoft/magentic-ui/tree/d3c9d13c39288257286a66daabf7c5b5fb72ee69) | MIT | servicio | Adaptador HTTP.  |
| 11 | `huginn` | [huginn/huginn@639c050b2b](https://github.com/huginn/huginn/tree/639c050b2bf4e14ef9983012af99dfc1dc68b334) | MIT | servicio | Adaptador HTTP. No tiene API JSON de lectura. Bloqueado. |
| 12 | `steel-browser` | [steel-dev/steel-browser@552550af79](https://github.com/steel-dev/steel-browser/tree/552550af79742a75fef24c24b1134e43e99e3d5e) | Apache-2.0 | servicio | Adaptador HTTP. Autoalojado sin autenticación propia. Solo tras proxy con token. |
| 13 | `datahub` | [datahub-project/datahub@164ce58a86](https://github.com/datahub-project/datahub/tree/164ce58a867afb6ee6ceac64c1c7aa9b526c1841) | Apache-2.0 | servicio | Adaptador HTTP.  |
| 14 | `jitsu` | [jitsucom/jitsu@6c0d189a55](https://github.com/jitsucom/jitsu/tree/6c0d189a55c9e6c7b47d024d046e091ff1636565) | MIT | servicio | Adaptador HTTP.  |
| 15 | `fides` | [ethyca/fides@e87f3ff835](https://github.com/ethyca/fides/tree/e87f3ff835af368defc1ec42dc29ec545a288585) | Apache-2.0 | servicio | Adaptador HTTP.  |
| 16 | `debezium` | [debezium/debezium@a4c282ea70](https://github.com/debezium/debezium/tree/a4c282ea70d3f913df699464f3e42f9ddb7eb03e) | Apache-2.0 | servicio | Adaptador HTTP.  |
| 17 | `operately` | [operately/operately@9fa8692fb6](https://github.com/operately/operately/tree/9fa8692fb61cec13730fb4523daf57c29261be45) | Apache-2.0 | servicio | Adaptador HTTP. Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 18 | `taguette` | [remram44/taguette@52fcdce957](https://github.com/remram44/taguette/tree/52fcdce95709375a4085cb10852bf7dd251ccb3d) | BSD-3-Clause | servicio | Adaptador HTTP.  |
| 19 | `seaweedfs` | [seaweedfs/seaweedfs@e0890391ac](https://github.com/seaweedfs/seaweedfs/tree/e0890391acff2e8cac6dea79c28e931ab1dfb70e) | Apache-2.0 | servicio | Adaptador HTTP. Sin autenticación por defecto (JWT opcional). Verificar el modo JWT en el commit fijado. |
| 20 | `caddy` | [caddyserver/caddy@7591cff1fb](https://github.com/caddyserver/caddy/tree/7591cff1fb03202ce022982af020197f3f387220) | Apache-2.0 | servicio | Adaptador HTTP. La API de administración no tiene autenticación y no debe exponerse. Solo detrás de un proxy con token; si no, no_aplica. |
| 21 | `valkey` | [valkey-io/valkey@c98c0e2e6c](https://github.com/valkey-io/valkey/tree/c98c0e2e6c271a24c829d17b2ed94d64c576c33f) | BSD-3-Clause | servicio | Adaptador HTTP. Protocolo RESP, no HTTP. Receta local con cliente oficial y comando fijo (INFO). |
| 22 | `tusd` | [tus/tusd@cec3998089](https://github.com/tus/tusd/tree/cec39980890809a9e7202872ec32f736f3b4a3f5) | MIT | servicio | Adaptador HTTP. Servidor de subidas sin API de lectura útil. Probable no_aplica. |
| 23 | `gotenberg` | [gotenberg/gotenberg@4d577e1467](https://github.com/gotenberg/gotenberg/tree/4d577e1467aaffa080b1e89d64ecb86c2fba4e98) | MIT | servicio | Adaptador HTTP. /health no pide credencial. Solo conectar con un modo "sin credencial" revisado; si no, marcar no_aplica. |
| 24 | `signoz` | [SigNoz/signoz@ca7daf8ea9](https://github.com/SigNoz/signoz/tree/ca7daf8ea974b879379101c7f7d8cb420da6acc7) | MIT | servicio | Adaptador HTTP. Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 25 | `postal` | [postalserver/postal@d96eddbade](https://github.com/postalserver/postal/tree/d96eddbadeda600595d6247486f9ceb8e99cbc15) | MIT | servicio | Adaptador HTTP. Su API es de envíos (POST). Sin lectura: bloqueado. |
| 26 | `crawl4ai` | [unclecode/crawl4ai@cae74b203a](https://github.com/unclecode/crawl4ai/tree/cae74b203a33994f7e13b9052c3b0d5c93daa0e6) | Apache-2.0 | servicio | Adaptador HTTP.  |
| 27 | `google-ads` | [googleads/google-ads-python@f253b400dc](https://github.com/googleads/google-ads-python/tree/f253b400dc5924b731fcb42dbcd99e485200581e) | Apache-2.0 | servicio | Adaptador HTTP. La librería oficial solo trae gRPC. Tomar la ruta REST GET customers:listAccessibleCustomers de la documentación oficial (versión v26 fijada). Necesita OAuth y developer-token (segundo secreto por variable VERDUGO_*). |
| 28 | `meta-ads` | [meta/facebook-python-business-sdk@b08e5c1d36](https://github.com/meta/facebook-python-business-sdk/tree/b08e5c1d36a2adad3c4ede6578654c8eaca5f225) | LicenseRef-Meta-Platform | servicio | Adaptador HTTP. El SDK manda access_token en la URL: prohibido. Solo conectar si la documentación oficial de Graph API confirma el encabezado Authorization: Bearer. |
| 29 | `bifrost` | [maximhq/bifrost@ff2e69f7f0](https://github.com/maximhq/bifrost/tree/ff2e69f7f0143ab79c9de5258b90bd9c70cf347b) | Apache-2.0 | servicio | Adaptador HTTP. Su API de administración usa sesiones o credenciales de administración; verificar en transports/bifrost-http/handlers/middlewares.go antes de elegir la autenticación. |
| 30 | `postgres` | [postgres/postgres@8d87367b39](https://github.com/postgres/postgres/tree/8d87367b39e44b0913ca585c733795cc2d30bff1) | PostgreSQL | servicio | Adaptador HTTP. No es HTTP. Leer vía PostgREST (componente) o con un driver de solo lectura en receta local. |
| 31 | `livekit` | [livekit/agents@59753ba7d7](https://github.com/livekit/agents/tree/59753ba7d759621ffb256b8023ebf2ddf70ffa9a) | Apache-2.0 | servicio | Adaptador HTTP. API Twirp por POST con JWT firmado con api_key/secret. Requiere firma local revisada. |
| 32 | `temporal` | [temporalio/temporal@03ecd1d228](https://github.com/temporalio/temporal/tree/03ecd1d228d2b8d9d433da55785afc9aeeead918) | MIT | servicio | Adaptador HTTP. Verificar la API HTTP (grpc-gateway) /api/v1/namespaces en el commit fijado. |
| 33 | `dagster` | [dagster-io/dagster@93e5f51da4](https://github.com/dagster-io/dagster/tree/93e5f51da49420d3e06d9399471070acedb554ca) | Apache-2.0 | servicio | Adaptador HTTP. Solo GraphQL. Una consulta estática fija en código, como Saleor; nunca GraphQL desde params. |
| 34 | `killbill` | [killbill/killbill@52e2f55f10](https://github.com/killbill/killbill/tree/52e2f55f103baf0703ddee71e10a7036595fc851) | Apache-2.0 | servicio | Adaptador HTTP. Usa dos secretos (X-Killbill-ApiKey/ApiSecret) más Basic. Diseñar el manejo de dos variables VERDUGO_*. |
| 35 | `otel-collector` | [open-telemetry/opentelemetry-collector@e366bb7fb4](https://github.com/open-telemetry/opentelemetry-collector/tree/e366bb7fb49a67fd117332fff93795a0050744ff) | Apache-2.0 | servicio | Adaptador HTTP.  |
| 36 | `mcp-gsc` | [AminForou/mcp-gsc@45291df024](https://github.com/AminForou/mcp-gsc/tree/45291df024c7873b2042c83d7add70ced7bb621f) | MIT | mcp | Registro MCP.  |
| 37 | `opengmb` | [synectus/OpenGMB@8f399472e9](https://github.com/synectus/OpenGMB/tree/8f399472e9d484cfcad77eef33b0da341e469577) | MIT | mcp | Registro MCP.  |
| 38 | `nlweb` | [microsoft/NLWeb@b423f15d9a](https://github.com/microsoft/NLWeb/tree/b423f15d9aeaa023ce75993ac9deed2354597043) | MIT | mcp | Registro MCP.  |
| 39 | `ipranges` | [lord-alfred/ipranges@d4ea6c582a](https://github.com/lord-alfred/ipranges/tree/d4ea6c582a509538907480e641bcee6821746bc3) | CC0-1.0 | datos | Datos fijados.  |
| 40 | `the-great-gpt-firewall` | [samber/the-great-gpt-firewall@60b2214d7b](https://github.com/samber/the-great-gpt-firewall/tree/60b2214d7b2cbd2c1b9d175afb31ad3024c085bb) | MIT | datos | Datos fijados.  |
| 41 | `local-seo-skills` | [garrettjsmith/localseoskills@c3b7a25b7d](https://github.com/garrettjsmith/localseoskills/tree/c3b7a25b7d5cc370752d74cfea240ccf992a24db) | MIT | mcp | Registro MCP.  |
| 42 | `a2a` | [a2aproject/A2A@4d7cda4b17](https://github.com/a2aproject/A2A/tree/4d7cda4b1754ed410e41bf3be7ad9ebc62afe3d3) | Apache-2.0 | protocolo | SDK A2A.  |
| 43 | `playwright-mcp` | [microsoft/playwright-mcp@78eca85361](https://github.com/microsoft/playwright-mcp/tree/78eca85361efb545a4c0f59b6140aef0721c5412) | Apache-2.0 | mcp | Registro MCP.  |
| 44 | `claude-skills-c-level` | [alirezarezvani/claude-skills@08cd8a9fc8](https://github.com/alirezarezvani/claude-skills/tree/08cd8a9fc86cc370e2c0d448e8171fbcfdbc5a30) | MIT | mcp | Registro MCP.  |
| 45 | `openprospector` | [clawnify/OpenProspector@dad0e778ff](https://github.com/clawnify/OpenProspector/tree/dad0e778ff4e1438b69574ff9cbb7663a3bda6e6) | MIT | biblioteca | Receta local.  |
| 46 | `openseo` | [duckduckdeploy/openseo@12b5254005](https://github.com/duckduckdeploy/openseo/tree/12b525400539f980668d088ff7154236a2376e88) | MIT | biblioteca | Receta local.  |
| 47 | `advertools` | [eliasdabbas/advertools@59dc2be7a9](https://github.com/eliasdabbas/advertools/tree/59dc2be7a98ab3bab2a711efacd5023f8ecffa14) | MIT | biblioteca | Receta local.  |
| 48 | `kingfisher-collect` | [open-contracting/kingfisher-collect@865bbb20ff](https://github.com/open-contracting/kingfisher-collect/tree/865bbb20ff4e6495bd2aba08bef5f2a0a1a648f6) | BSD-3-Clause | biblioteca | Receta local.  |
| 49 | `markitdown` | [microsoft/markitdown@ed178952a6](https://github.com/microsoft/markitdown/tree/ed178952a6672abdfd35b5f9e76a80b6cefc086e) | MIT | biblioteca | Receta local.  |
| 50 | `spacy` | [explosion/spaCy@7ff14d4da8](https://github.com/explosion/spaCy/tree/7ff14d4da84817f84c32b980882178ddacc066a1) | MIT | biblioteca | Receta local.  |

## Tanda 2 — bibliotecas (marketing, autoridad, agentes, motor de datos) (50)

| # | Pieza | Repositorio @ commit | Licencia | Tipo | Qué hacer / nota |
|---|---|---|---|---|---|
| 1 | `parsedmarc` | [domainaware/parsedmarc@70a0ea0470](https://github.com/domainaware/parsedmarc/tree/70a0ea0470d04649e33e6b09ce20da991d424f72) | Apache-2.0 | biblioteca | Receta local.  |
| 2 | `geo-optimizer` | [Auriti-Labs/geo-optimizer-skill@b7fd7dfaae](https://github.com/Auriti-Labs/geo-optimizer-skill/tree/b7fd7dfaaeb9a28841954ac373236211813ca5f2) | MIT | biblioteca | Receta local.  |
| 3 | `geo-lint` | [IJONIS/geo-lint@b2d79319d1](https://github.com/IJONIS/geo-lint/tree/b2d79319d1d0d4d4fc5d6abbc4ce5156afc5d14b) | MIT | biblioteca | Receta local.  |
| 4 | `autogeo` | [cxcscmu/AutoGEO@49456df236](https://github.com/cxcscmu/AutoGEO/tree/49456df236774ea24087c44f45e9e52005b8e6a4) | MIT | biblioteca | Receta local.  |
| 5 | `site-md` | [yazinsai/site-md@c5c31bc781](https://github.com/yazinsai/site-md/tree/c5c31bc781d06f83a81d30a284f0df3aa2ffbe32) | MIT | biblioteca | Receta local.  |
| 6 | `seo-graph` | [jdevalk/seo-graph@c33eb1e120](https://github.com/jdevalk/seo-graph/tree/c33eb1e120c620970042e28f1332fc90c30125e6) | MIT | biblioteca | Receta local.  |
| 7 | `structured-data-validator` | [adobe/structured-data-validator@6918b52651](https://github.com/adobe/structured-data-validator/tree/6918b52651d6f4c5dae612859e2e395de5a1910e) | Apache-2.0 | biblioteca | Receta local.  |
| 8 | `pywikibot` | [wikimedia/pywikibot@b8ccec48b3](https://github.com/wikimedia/pywikibot/tree/b8ccec48b3c26211cd498e27a5ca6eb071627cb1) | MIT | biblioteca | Receta local.  |
| 9 | `indexnow-for-python` | [jakob-bagterp/index-now-for-python@47e9f82412](https://github.com/jakob-bagterp/index-now-for-python/tree/47e9f82412e95a55b2c177ca66d79786117349c6) | MIT | biblioteca | Receta local.  |
| 10 | `cdx-toolkit` | [cocrawler/cdx_toolkit@e87b120499](https://github.com/cocrawler/cdx_toolkit/tree/e87b1204993b77a4c41c03239baefa1c8462a6e1) | Apache-2.0 | biblioteca | Receta local.  |
| 11 | `cc-webgraph` | [commoncrawl/cc-webgraph@8a3a34e2f3](https://github.com/commoncrawl/cc-webgraph/tree/8a3a34e2f3bc16b865ee234eab83a4917086b814) | Apache-2.0 | biblioteca | Receta local.  |
| 12 | `trendspyg` | [flack0x/trendspyg@9f07b2573e](https://github.com/flack0x/trendspyg/tree/9f07b2573e7287df85df9202da206569024723e9) | MIT | biblioteca | Receta local.  |
| 13 | `waybackpy` | [akamhy/waybackpy@3b3e78d901](https://github.com/akamhy/waybackpy/tree/3b3e78d901a600bb22943202c6a8981ca04a5e48) | MIT | biblioteca | Receta local.  |
| 14 | `newsjack` | [elvisun/newsjack@c2df3a0168](https://github.com/elvisun/newsjack/tree/c2df3a0168083d620b9b36518aeca16a4eb72296) | MIT | biblioteca | Receta local.  |
| 15 | `gdeltdoc` | [alex9smith/gdelt-doc-api@41220163fb](https://github.com/alex9smith/gdelt-doc-api/tree/41220163fbab99982e4dca3a05d25a95b49896d7) | MIT | biblioteca | Receta local.  |
| 16 | `news-please` | [fhamborg/news-please@f899850be2](https://github.com/fhamborg/news-please/tree/f899850be2bb0059da101c13502ec88af057f974) | Apache-2.0 | biblioteca | Receta local.  |
| 17 | `python-podcastindex` | [piqosoft/python-podcastindex@63fdb84b76](https://github.com/piqosoft/python-podcastindex/tree/63fdb84b76b5d65c99e9c92428af55cc51aff04e) | MIT | biblioteca | Receta local.  |
| 18 | `praw` | [praw-dev/praw@4590cb5b0a](https://github.com/praw-dev/praw/tree/4590cb5b0ad2f9afbab983d60d792fc3c74d1f45) | BSD-2-Clause | biblioteca | Receta local.  |
| 19 | `youtube-comment-downloader` | [egbertbouman/youtube-comment-downloader@3f557bc802](https://github.com/egbertbouman/youtube-comment-downloader/tree/3f557bc8023d9e3ab9edda93bcd516ca2b33d3c1) | MIT | biblioteca | Receta local.  |
| 20 | `people-also-ask` | [labsonmars/people_also_ask@21db28fb5a](https://github.com/labsonmars/people_also_ask/tree/21db28fb5a75d233bf18db381fab538791eee495) | MIT | biblioteca | Receta local.  |
| 21 | `c2pa` | [contentauth/c2pa-rs@0e92435c6d](https://github.com/contentauth/c2pa-rs/tree/0e92435c6d621c02c9bde2a8d82346295ed1f509) | Apache-2.0 OR MIT | biblioteca | Receta local.  |
| 22 | `ckanapi` | [ckan/ckanapi@94b8c24a21](https://github.com/ckan/ckanapi/tree/94b8c24a21a185c270a01bcbcfa72ff4e1b78b1c) | MIT | biblioteca | Receta local.  |
| 23 | `crewai` | [crewAIInc/crewAI@d7dfa0ef5a](https://github.com/crewAIInc/crewAI/tree/d7dfa0ef5ade793bd48ff7357c6eb45a45294371) | MIT | biblioteca | Receta local.  |
| 24 | `openai-agents` | [openai/openai-agents-python@64fbde5d02](https://github.com/openai/openai-agents-python/tree/64fbde5d02b42ae5f9db668eb0184cdb3fc9d775) | MIT | biblioteca | Receta local.  |
| 25 | `google-adk` | [google/adk-python@12aab4aaaa](https://github.com/google/adk-python/tree/12aab4aaaa1a72e3edcc65fa4f9d849896ea6c48) | Apache-2.0 | biblioteca | Receta local.  |
| 26 | `agent-framework` | [microsoft/agent-framework@92838b6049](https://github.com/microsoft/agent-framework/tree/92838b60498395142cb8b74693353163e95a0faf) | MIT | biblioteca | Receta local.  |
| 27 | `smolagents` | [huggingface/smolagents@96f33faaf0](https://github.com/huggingface/smolagents/tree/96f33faaf028479119ec8d34507b47694cf14e34) | Apache-2.0 | biblioteca | Receta local.  |
| 28 | `camel` | [camel-ai/camel@0366b64bf3](https://github.com/camel-ai/camel/tree/0366b64bf3609c76f50e396715aab73ba58a930c) | Apache-2.0 | biblioteca | Receta local.  |
| 29 | `any-agent` | [mozilla-ai/any-agent@a469723ac4](https://github.com/mozilla-ai/any-agent/tree/a469723ac4a0518ab0696d57e09e4dc407c826ec) | Apache-2.0 | biblioteca | Receta local.  |
| 30 | `langchain` | [langchain-ai/langchain@ea17e48f0a](https://github.com/langchain-ai/langchain/tree/ea17e48f0a4336c920394fd029de99f1568b4c38) | MIT | biblioteca | Receta local.  |
| 31 | `langgraph-supervisor` | [langchain-ai/langgraph-supervisor-py@88859b3401](https://github.com/langchain-ai/langgraph-supervisor-py/tree/88859b34017ac3569bbd4a3092c7e77593a0a960) | MIT | biblioteca | Receta local.  |
| 32 | `mem0` | [mem0ai/mem0@f1791daa86](https://github.com/mem0ai/mem0/tree/f1791daa86d469249c9b002f62644d58a1eb96a0) | Apache-2.0 | biblioteca | Receta local.  |
| 33 | `graphiti` | [getzep/graphiti@3ed0252749](https://github.com/getzep/graphiti/tree/3ed02527499d4eb3b2eb133d716898dc89d7cc99) | Apache-2.0 | biblioteca | Receta local.  |
| 34 | `browser-use` | [browser-use/browser-use@480d0bd508](https://github.com/browser-use/browser-use/tree/480d0bd508ce10dcf27a4716f2f87355a08e8372) | MIT | biblioteca | Receta local.  |
| 35 | `mcp-python-sdk` | [modelcontextprotocol/python-sdk@77001c96f9](https://github.com/modelcontextprotocol/python-sdk/tree/77001c96f9507be0f4d009b83210a384a5e08bda) | MIT | biblioteca | Receta local.  |
| 36 | `fastmcp` | [PrefectHQ/fastmcp@a8745d61e6](https://github.com/PrefectHQ/fastmcp/tree/a8745d61e650467756bb28b4157822dbfbdfa34f) | Apache-2.0 | biblioteca | Receta local.  |
| 37 | `mcp-agent` | [lastmile-ai/mcp-agent@f62d849350](https://github.com/lastmile-ai/mcp-agent/tree/f62d849350816588b1c6294e7914bbe4d8b84072) | Apache-2.0 | biblioteca | Receta local.  |
| 38 | `guardrails` | [guardrails-ai/guardrails@06d0ff2c5f](https://github.com/guardrails-ai/guardrails/tree/06d0ff2c5f9bcb493d976b76f885e37e41ce845d) | Apache-2.0 | biblioteca | Receta local.  |
| 39 | `nemo-guardrails` | [NVIDIA/NeMo-Guardrails@5d7f4c1ca6](https://github.com/NVIDIA/NeMo-Guardrails/tree/5d7f4c1ca62fb6155066e6c581379d1a5ec11338) | Apache-2.0 | biblioteca | Receta local.  |
| 40 | `instructor` | [567-labs/instructor@2549049be0](https://github.com/567-labs/instructor/tree/2549049be07ec3be1d617f8904ea8ffe18253c48) | MIT | biblioteca | Receta local.  |
| 41 | `outlines` | [dottxt-ai/outlines@c52af8472c](https://github.com/dottxt-ai/outlines/tree/c52af8472c6fe8a607a733ec11b709476af77a96) | Apache-2.0 | biblioteca | Receta local.  |
| 42 | `storm` | [stanford-oval/storm@fb951af774](https://github.com/stanford-oval/storm/tree/fb951af7744dab086e34962e9bc6fe878e145f83) | MIT | biblioteca | Receta local.  |
| 43 | `humanlayer` | [humanlayer/humanlayer@b7ad8e1d38](https://github.com/humanlayer/humanlayer/tree/b7ad8e1d383ff0f5fbec7bdc30425e4a59d5f789) | Apache-2.0 | biblioteca | Receta local.  |
| 44 | `cua` | [trycua/cua@c372e5fb2b](https://github.com/trycua/cua/tree/c372e5fb2bae944974e903fbf117c61f4ced696e) | MIT | biblioteca | Receta local.  |
| 45 | `llm-guard` | [protectai/llm-guard@168c1034ff](https://github.com/protectai/llm-guard/tree/168c1034ffdb33837e7ae6fd6a16b80567c1be03) | MIT | biblioteca | Receta local.  |
| 46 | `a2a-python` | [a2aproject/a2a-python@09c93473a7](https://github.com/a2aproject/a2a-python/tree/09c93473a77d0a18be8429ad71958211b736a8c0) | Apache-2.0 | biblioteca | Receta local.  |
| 47 | `splink` | [moj-analytical-services/splink@f319070e56](https://github.com/moj-analytical-services/splink/tree/f319070e56c5b3666ec512811ac1820070f6f2e5) | MIT | biblioteca | Receta local.  |
| 48 | `iceberg` | [apache/iceberg@234d55774d](https://github.com/apache/iceberg/tree/234d55774d3c7355f92c8e93f8e117b70726e556) | Apache-2.0 | biblioteca | Receta local.  |
| 49 | `arrow` | [apache/arrow@ab5b42237d](https://github.com/apache/arrow/tree/ab5b42237dfe14d683bc74ecbddf71109a0c6633) | Apache-2.0 | biblioteca | Receta local. LICENSE.txt incluye avisos MIT de terceros. |
| 50 | `polars` | [pola-rs/polars@5c36cdd75a](https://github.com/pola-rs/polars/tree/5c36cdd75a30a8ab12a9f70e251c0f267235b2a7) | MIT | biblioteca | Receta local.  |

## Tanda 3 — programas de línea de comandos (requiere runner nuevo) y bibliotecas (50)

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
| 22 | `ibis` | [ibis-project/ibis@6d40f963fe](https://github.com/ibis-project/ibis/tree/6d40f963fee940063e09956c7e60d073f4302259) | Apache-2.0 | biblioteca | Receta local.  |
| 23 | `feast` | [feast-dev/feast@108c96704d](https://github.com/feast-dev/feast/tree/108c96704daa72015d8f447a5d503de964c45b3f) | Apache-2.0 | biblioteca | Receta local.  |
| 24 | `openlineage` | [OpenLineage/OpenLineage@c41626e99a](https://github.com/OpenLineage/OpenLineage/tree/c41626e99af0a02ad95a2805979167ad948ecb7b) | Apache-2.0 | biblioteca | Receta local.  |
| 25 | `apache-age` | [apache/age@8c7e44fd2a](https://github.com/apache/age/tree/8c7e44fd2a525dedfd3d4e8168921442eb4fce2f) | Apache-2.0 | biblioteca | Receta local.  |
| 26 | `causalml` | [uber/causalml@d59bb520fc](https://github.com/uber/causalml/tree/d59bb520fc78410c01c443bad0ac57ea972844b8) | Apache-2.0 | biblioteca | Receta local.  |
| 27 | `causal-learn` | [py-why/causal-learn@0dacacf363](https://github.com/py-why/causal-learn/tree/0dacacf36390e3084704636bc3c36e82e35ee0cc) | MIT | biblioteca | Receta local.  |
| 28 | `tfcausalimpact` | [WillianFuks/tfcausalimpact@99bd5fb866](https://github.com/WillianFuks/tfcausalimpact/tree/99bd5fb866acb352daf1b58c17d8f711d0e1a9ec) | Apache-2.0 | biblioteca | Receta local.  |
| 29 | `pandera` | [unionai-oss/pandera@0292915e33](https://github.com/unionai-oss/pandera/tree/0292915e3321e83ee19380d7329788b7ead05291) | MIT | biblioteca | Receta local.  |
| 30 | `ydata-profiling` | [ydataai/ydata-profiling@7f43aac68b](https://github.com/ydataai/ydata-profiling/tree/7f43aac68b2539bfe8f487f315aeaf44e965d29a) | MIT | biblioteca | Receta local.  |
| 31 | `opendp` | [opendp/opendp@11887ec1aa](https://github.com/opendp/opendp/tree/11887ec1aa392f9f1cc08a37cf938962babac7a1) | MIT | biblioteca | Receta local.  |
| 32 | `flaml` | [microsoft/FLAML@46bce0ce98](https://github.com/microsoft/FLAML/tree/46bce0ce989aae0271e68e5daac5b8a9b0522b87) | MIT | biblioteca | Receta local.  |
| 33 | `chronos` | [amazon-science/chronos-forecasting@1224fafa91](https://github.com/amazon-science/chronos-forecasting/tree/1224fafa91e1ecd6674f5204066b159e40b5e4a1) | Apache-2.0 | biblioteca | Receta local.  |
| 34 | `recommenders` | [recommenders-team/recommenders@cc47866b05](https://github.com/recommenders-team/recommenders/tree/cc47866b0599721f8544d1cc850a5a1db091acb3) | MIT | biblioteca | Receta local.  |
| 35 | `shap` | [shap/shap@511710def9](https://github.com/shap/shap/tree/511710def94e163a4678a1be07a74b9ccf0a4124) | MIT | biblioteca | Receta local.  |
| 36 | `sentence-transformers` | [UKPLab/sentence-transformers@688fd663e7](https://github.com/UKPLab/sentence-transformers/tree/688fd663e7b242f41f3f62296d08c69937efeb00) | Apache-2.0 | biblioteca | Receta local.  |
| 37 | `transformers` | [huggingface/transformers@0d7a621917](https://github.com/huggingface/transformers/tree/0d7a6219179b24586089ae81b45cf725078e681f) | Apache-2.0 | biblioteca | Receta local.  |
| 38 | `gliner` | [urchade/GLiNER@beb41b3839](https://github.com/urchade/GLiNER/tree/beb41b3839267952d0f063c04dd6236e9fd93a38) | Apache-2.0 | biblioteca | Receta local.  |
| 39 | `arx` | [arx-deidentifier/arx@4e0a5f5340](https://github.com/arx-deidentifier/arx/tree/4e0a5f5340fe9a58c44b34c2f9acd2d68f1dad5f) | Apache-2.0 | biblioteca | Receta local.  |
| 40 | `river` | [online-ml/river@115df63c9c](https://github.com/online-ml/river/tree/115df63c9cd57f904dd3a6d586b6cf32d2c1b2c8) | BSD-3-Clause | biblioteca | Receta local.  |
| 41 | `vowpal` | [VowpalWabbit/vowpal_wabbit@00196b35f6](https://github.com/VowpalWabbit/vowpal_wabbit/tree/00196b35f63bcb8a6d66966e2b4cf67d6a2bd335) | BSD-3-Clause | biblioteca | Receta local.  |
| 42 | `ax` | [facebook/Ax@fd8a67a524](https://github.com/facebook/Ax/tree/fd8a67a524b063b2615815c638af2c94b034f476) | MIT | biblioteca | Receta local.  |
| 43 | `faker` | [joke2k/faker@affa2c5aad](https://github.com/joke2k/faker/tree/affa2c5aada23fc5c00127298a8e904375d32832) | MIT | biblioteca | Receta local.  |
| 44 | `sqlglot` | [tobymao/sqlglot@b476d29f42](https://github.com/tobymao/sqlglot/tree/b476d29f42eeabfd0c8a150b9239a344b02e68dd) | MIT | biblioteca | Receta local.  |
| 45 | `great-tables` | [posit-dev/great-tables@193bfc23b0](https://github.com/posit-dev/great-tables/tree/193bfc23b03a034aa5da8a1e7b471840ac2f3f8e) | MIT | biblioteca | Receta local.  |
| 46 | `cognee` | [topoteretes/cognee@4053f6cc55](https://github.com/topoteretes/cognee/tree/4053f6cc5536757f26a3665eed95c50088e6dc0b) | Apache-2.0 | biblioteca | Receta local.  |
| 47 | `pyod` | [yzhao062/pyod@9680a8b9d7](https://github.com/yzhao062/pyod/tree/9680a8b9d767d8226f76e5b3157ed318af881d74) | BSD-2-Clause | biblioteca | Receta local.  |
| 48 | `mapie` | [scikit-learn-contrib/MAPIE@d5ea5e07ae](https://github.com/scikit-learn-contrib/MAPIE/tree/d5ea5e07aea09a897726fd8641c193850a5c540d) | BSD-3-Clause | biblioteca | Receta local.  |
| 49 | `lifelines` | [CamDavidsonPilon/lifelines@7a8fc34a01](https://github.com/CamDavidsonPilon/lifelines/tree/7a8fc34a013ecd79fa405017b89e1697c1cc6e17) | MIT | biblioteca | Receta local.  |
| 50 | `datasketch` | [ekzhu/datasketch@c7eaaeea3f](https://github.com/ekzhu/datasketch/tree/c7eaaeea3f39909f906a9cf8ad4d21a878cb4e07) | MIT | biblioteca | Receta local.  |

## Tanda 4 — bibliotecas restantes (35)

| # | Pieza | Repositorio @ commit | Licencia | Tipo | Qué hacer / nota |
|---|---|---|---|---|---|
| 1 | `h3` | [uber/h3@15920096d4](https://github.com/uber/h3/tree/15920096d4a165729c01f749e2bd97334b009519) | Apache-2.0 | biblioteca | Receta local.  |
| 2 | `tinytroupe` | [microsoft/TinyTroupe@7ce8be378a](https://github.com/microsoft/TinyTroupe/tree/7ce8be378a37ee73f9745d6781452712318afa04) | MIT | biblioteca | Receta local.  |
| 3 | `gpt-researcher` | [assafelovic/gpt-researcher@ddd4db3620](https://github.com/assafelovic/gpt-researcher/tree/ddd4db36208d9c8e49f3b2436efda97baecb5433) | Apache-2.0 | biblioteca | Receta local.  |
| 4 | `forecasting-tools` | [Metaculus/forecasting-tools@bd7e6a65e7](https://github.com/Metaculus/forecasting-tools/tree/bd7e6a65e7f01141af8cab411ff8f51f908f8061) | MIT | biblioteca | Receta local.  |
| 5 | `datosmex` | [andreslomeliv/DatosMex@4179265209](https://github.com/andreslomeliv/DatosMex/tree/4179265209ca8345cc2de533f82612a6ca45314f) | MIT | biblioteca | Receta local. MIT en las subcarpetas BANXICOpy e INEGIpy. |
| 6 | `wbgapi` | [tgherzog/wbgapi@4d0d2c925a](https://github.com/tgherzog/wbgapi/tree/4d0d2c925a8dac359df5a2d9e82001ff6feeecda) | MIT | biblioteca | Receta local.  |
| 7 | `census` | [datamade/census@3da5a10681](https://github.com/datamade/census/tree/3da5a1068164c27f6e83815f5d28ec300e184fdf) | BSD-3-Clause | biblioteca | Receta local.  |
| 8 | `comtradeapicall` | [uncomtrade/comtradeapicall@d8b1958898](https://github.com/uncomtrade/comtradeapicall/tree/d8b19588986405df8c3c94062bd73fd08b9110cd) | MIT | biblioteca | Receta local.  |
| 9 | `py-ecomplexity` | [cid-harvard/py-ecomplexity@d22c0f7fca](https://github.com/cid-harvard/py-ecomplexity/tree/d22c0f7fcad4cf629415895dd17afc5685108274) | MIT | biblioteca | Receta local.  |
| 10 | `openbb` | [OpenBB-finance/OpenBB@e43353a828](https://github.com/OpenBB-finance/OpenBB/tree/e43353a82815ff9ba56ad1b7ad47c32729dcf314) | Apache-2.0 | biblioteca | Receta local.  |
| 11 | `financetoolkit` | [JerBouma/FinanceToolkit@375f820d8f](https://github.com/JerBouma/FinanceToolkit/tree/375f820d8f84e90e2f42f5d413ed67056cbd4256) | MIT | biblioteca | Receta local.  |
| 12 | `jobspy` | [speedyapply/JobSpy@68b88d6909](https://github.com/speedyapply/JobSpy/tree/68b88d6909a2342ad75fbb945c4204a3a7ed6665) | MIT | biblioteca | Receta local.  |
| 13 | `osmnx` | [gboeing/osmnx@5f3b46f048](https://github.com/gboeing/osmnx/tree/5f3b46f048f9f0a693702cea5f29f2eaad840204) | MIT | biblioteca | Receta local.  |
| 14 | `bertopic` | [MaartenGr/BERTopic@9036123c97](https://github.com/MaartenGr/BERTopic/tree/9036123c97aaa9a6cc4bec4a6db1a7caf9209df6) | MIT | biblioteca | Receta local.  |
| 15 | `pricesensitivitymeter` | [max-alletsee/pricesensitivitymeter@8188de1e95](https://github.com/max-alletsee/pricesensitivitymeter/tree/8188de1e95fa0f407073677f6f88baec2f43c8d4) | MIT | biblioteca | Receta local. Licencia MIT de R (archivo corto con año y titular). |
| 16 | `statsforecast` | [Nixtla/statsforecast@652a4e940f](https://github.com/Nixtla/statsforecast/tree/652a4e940f4f7993d894cdff74ac6ec9a5f01247) | Apache-2.0 | biblioteca | Receta local.  |
| 17 | `statsmodels` | [statsmodels/statsmodels@27e7475960](https://github.com/statsmodels/statsmodels/tree/27e747596049cc1a9b06e113af739fdeec59cecc) | BSD-3-Clause | biblioteca | Receta local.  |
| 18 | `mlxtend` | [rasbt/mlxtend@1aee767ef5](https://github.com/rasbt/mlxtend/tree/1aee767ef57b84a8191511a08955c583b65de382) | BSD-3-Clause | biblioteca | Receta local. Código BSD-3; documentación CC-BY. |
| 19 | `networkx` | [networkx/networkx@6855cd5869](https://github.com/networkx/networkx/tree/6855cd586982cc2e4710b8eb87251ccf56674bf1) | BSD-3-Clause | biblioteca | Receta local.  |
| 20 | `pymcdm` | [kotbaton/pymcdm@346a44f5af](https://github.com/kotbaton/pymcdm/tree/346a44f5afdac249c534912cc8d483e82586c52d) | MIT | biblioteca | Receta local.  |
| 21 | `nashpy` | [drvinceknight/Nashpy@a797cfd91e](https://github.com/drvinceknight/Nashpy/tree/a797cfd91e065f1ac67f9660b27d487627ec5528) | MIT | biblioteca | Receta local.  |
| 22 | `mesa` | [projectmesa/mesa@2d9b251776](https://github.com/projectmesa/mesa/tree/2d9b25177627f38fb43c4273ac2bdd03b95f01cb) | Apache-2.0 | biblioteca | Receta local.  |
| 23 | `pysd` | [SDXorg/pysd@8991d119e1](https://github.com/SDXorg/pysd/tree/8991d119e139029d4dec712d257cf5fcc3549b8f) | MIT | biblioteca | Receta local.  |
| 24 | `numpy-financial` | [numpy/numpy-financial@031ed55d32](https://github.com/numpy/numpy-financial/tree/031ed55d322b7aad57311b9d63b589c79df942a1) | BSD-3-Clause | biblioteca | Receta local.  |
| 25 | `graphrag` | [microsoft/graphrag@34b2b67ae4](https://github.com/microsoft/graphrag/tree/34b2b67ae4601ad0b47bcd179fbe3f2a23aa0857) | MIT | biblioteca | Receta local.  |
| 26 | `vanna` | [vanna-ai/vanna@365d0617c1](https://github.com/vanna-ai/vanna/tree/365d0617c1a4567ffee1b19b40c27feb4206bfcf) | MIT | biblioteca | Receta local.  |
| 27 | `pymc-marketing` | [pymc-labs/pymc-marketing@4b4fead2b8](https://github.com/pymc-labs/pymc-marketing/tree/4b4fead2b899dbf1982d12aab3b0cb1dfbe635fb) | Apache-2.0 | biblioteca | Receta local.  |
| 28 | `pydantic-ai` | [pydantic/pydantic-ai@21b2f46740](https://github.com/pydantic/pydantic-ai/tree/21b2f46740f95a260bd492385c4638094015ec06) | MIT | biblioteca | Receta local.  |
| 29 | `dspy` | [stanfordnlp/dspy@3983960123](https://github.com/stanfordnlp/dspy/tree/398396012371a95471c8e7be24a70e6660e87aa4) | MIT | biblioteca | Receta local.  |
| 30 | `pgvector` | [pgvector/pgvector@66accb3af6](https://github.com/pgvector/pgvector/tree/66accb3af6705ea9975a33f6704f1cde50d99447) | PostgreSQL | biblioteca | Receta local.  |
| 31 | `docling` | [docling-project/docling@a7760abf0c](https://github.com/docling-project/docling/tree/a7760abf0ca53321a3fb5ae9b1a65b584bb743b9) | MIT | biblioteca | Receta local.  |
| 32 | `robyn` | [facebookexperimental/Robyn@aab4226ed5](https://github.com/facebookexperimental/Robyn/tree/aab4226ed5e40196cdbd82ff7fbbff55e91e1f58) | MIT | biblioteca | Receta local.  |
| 33 | `meridian` | [google/meridian@f4ca39d406](https://github.com/google/meridian/tree/f4ca39d406e1a86bd13d65fdf14166268044fd2d) | Apache-2.0 | biblioteca | Receta local.  |
| 34 | `pipecat` | [pipecat-ai/pipecat@d5dd211c15](https://github.com/pipecat-ai/pipecat/tree/d5dd211c15055a78431a391188e0748edd4b2661) | BSD-2-Clause | biblioteca | Receta local.  |
| 35 | `whisper` | [openai/whisper@86098128c0](https://github.com/openai/whisper/tree/86098128c0b4f24f0e2aa2994de830614b474227) | MIT | biblioteca | Receta local.  |

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

