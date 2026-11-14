# Verdugo Digital v0.14 — Catálogo unificado: 300 libres + 22 excluidos

Observado y fijado por commit el 13 de noviembre de 2026. La licencia se leyó del archivo
de licencia en la raíz de **cada commit fijado** (clon git sin blobs, sin ejecutar código).
Es una clasificación técnica, **no una revisión legal**: `license_review` sigue en
`pending` y un abogado de propiedad intelectual de software debe confirmarla antes de vender.

| Estado | Cuántos |
|---|---|
| Libre | 285 |
| Libre (sin carpeta enterprise) | 12 |
| Libre con condición | 3 |
| **Excluido** | 22 |
| **Total registrado** | 322 |
| **Portafolio libre (todo menos excluidos)** | 300 |

Registrar un proyecto **no** es integrarlo: casi todos los proyectos nuevos aún no tienen
adaptador en el motor. El estado real lo da `python -m verdugo --state :memory: status`.

## Núcleo original del motor (100 del catálogo v0.8) (100)

| # | ID | Repositorio | Licencia | Política | Nota |
|---|---|---|---|---|---|
| 1 | `twenty` | [twentyhq/twenty](https://github.com/twentyhq/twenty/tree/e7f3c8579a49e02b9ee0cd655c1c8e3ba57100e9) | AGPL-3.0 | **Excluido** | Archivos @license Enterprise bajo licencia comercial. |
| 2 | `frappe-crm` | [frappe/crm](https://github.com/frappe/crm/tree/d68ef63d1eb239fbe60b56bfd9f74a44ad364a94) | AGPL-3.0 | **Excluido** |  |
| 3 | `erpnext` | [frappe/erpnext](https://github.com/frappe/erpnext/tree/2470b9dd004284e0c7ee00ed225da7d38a80a75d) | GPL-3.0 | **Excluido** |  |
| 4 | `odoo` | [odoo/odoo](https://github.com/odoo/odoo/tree/688cb908f74df65d1e71822338b1b60a124b17f8) | LGPL-3.0 | **Excluido** |  |
| 5 | `mautic` | [mautic/mautic](https://github.com/mautic/mautic/tree/229e8f7b0fcc0c1fd0013d51450a27afebd6f3b7) | GPL-3.0 | **Excluido** |  |
| 6 | `chatwoot` | [chatwoot/chatwoot](https://github.com/chatwoot/chatwoot/tree/309c63f359a1206caf9a36a271407f3bb4cc9419) | MIT | Libre (sin carpeta enterprise) | Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 7 | `listmonk` | [knadh/listmonk](https://github.com/knadh/listmonk/tree/32078ede6d87c83f4948cc592c76bee91d629f0b) | AGPL-3.0 | **Excluido** |  |
| 8 | `dittofeed` | [dittofeed/dittofeed](https://github.com/dittofeed/dittofeed/tree/91277939a9afcee797ab2562025f6b02d823b00c) | MIT | Libre |  |
| 9 | `novu` | [novuhq/novu](https://github.com/novuhq/novu/tree/a58cd5e532238f2a0e09631fc9d0967d1158aa0f) | MIT | Libre (sin carpeta enterprise) | Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 10 | `easyappointments` | [alextselegidis/easyappointments](https://github.com/alextselegidis/easyappointments/tree/f6c8a4c2f364bf8c64b1f913a531a7134dcfd3c6) | GPL-3.0 | **Excluido** |  |
| 11 | `astro` | [withastro/astro](https://github.com/withastro/astro/tree/d68e4f6340409a201df7c5f77d5d322abfe6c377) | MIT | Libre |  |
| 12 | `payload` | [payloadcms/payload](https://github.com/payloadcms/payload/tree/7a80820ce48dc71420d92e32ca076dc7d004375e) | MIT | Libre |  |
| 13 | `ghost` | [TryGhost/Ghost](https://github.com/TryGhost/Ghost/tree/45de48a161017375d40e874c8bc2a9f13e2b6f17) | MIT | Libre |  |
| 14 | `grapesjs` | [GrapesJS/grapesjs](https://github.com/GrapesJS/grapesjs/tree/e023d69b9fa97fbbc693052c9818f0c477b105a5) | BSD-3-Clause | Libre | Licencia en packages/core/LICENSE. |
| 15 | `formbricks` | [formbricks/formbricks](https://github.com/formbricks/formbricks/tree/31264bb7c6d747b31cd94cce8064b706d420a58a) | AGPL-3.0 | **Excluido** |  |
| 16 | `documenso` | [documenso/documenso](https://github.com/documenso/documenso/tree/f32ab10dc7189d3c375fc112469cbb156c9adb6f) | AGPL-3.0 | **Excluido** |  |
| 17 | `postiz` | [gitroomhq/postiz-app](https://github.com/gitroomhq/postiz-app/tree/b31d29fa4132a08aa82f728227df2938ccab7972) | AGPL-3.0 | **Excluido** |  |
| 18 | `dub` | [dubinc/dub.link](https://github.com/dubinc/dub.link/tree/6b463b4bdd9ed2fd9aa416f67b5b77d317b1471e) | AGPL-3.0 | **Excluido** |  |
| 19 | `shlink` | [shlinkio/shlink](https://github.com/shlinkio/shlink/tree/1f014cbc9f47a348e714890f0581d150a4ab102c) | MIT | Libre |  |
| 20 | `react-email` | [resend/react-email](https://github.com/resend/react-email/tree/e769155fc8a9aa878ec7d2e42efbc74cd7ab11bc) | MIT | Libre |  |
| 21 | `comfyui` | [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI/tree/74eb0c4b8a1a894e7210326882a8d9a016e37ccb) | GPL-3.0 | **Excluido** |  |
| 22 | `remotion` | [remotion-dev/remotion](https://github.com/remotion-dev/remotion/tree/eeb428f095529f52d359ecc709a174eff978642d) | LicenseRef-Remotion | **Excluido** | Licencia propia: gratis solo hasta 3 empleados. |
| 23 | `scrapy` | [scrapy/scrapy](https://github.com/scrapy/scrapy/tree/f7b1fd3f2f57c9d01f45276c1c3194f58cb0c1ea) | BSD-3-Clause | Libre |  |
| 24 | `crawlee` | [apify/crawlee](https://github.com/apify/crawlee/tree/393ecd732aa00420e188c85a93ec4a4d6479d9d0) | Apache-2.0 | Libre |  |
| 25 | `playwright` | [microsoft/playwright](https://github.com/microsoft/playwright/tree/392ab0f0de39feb99dbe71eb5fea61e7ad07a480) | Apache-2.0 | Libre |  |
| 26 | `changedetection` | [dgtlmoon/changedetection.io](https://github.com/dgtlmoon/changedetection.io/tree/1882705fd7f34aa74b9ee8512b242f7d402821e5) | Apache-2.0 | Libre |  |
| 27 | `trafilatura` | [adbar/trafilatura](https://github.com/adbar/trafilatura/tree/9c27981f4b7034a3249c77c4c06aaaed719fae66) | Apache-2.0 | Libre |  |
| 28 | `crawl4ai` | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai/tree/cae74b203a33994f7e13b9052c3b0d5c93daa0e6) | Apache-2.0 | Libre |  |
| 29 | `lighthouse` | [GoogleChrome/lighthouse](https://github.com/GoogleChrome/lighthouse/tree/5313024aa05786138dfd38c6740ef354e20c3f92) | Apache-2.0 | Libre |  |
| 30 | `lighthouse-ci` | [GoogleChrome/lighthouse-ci](https://github.com/GoogleChrome/lighthouse-ci/tree/3ead206a96a5ba714c386affe274576ccb8c09a9) | Apache-2.0 | Libre |  |
| 31 | `google-ads` | [googleads/google-ads-python](https://github.com/googleads/google-ads-python/tree/f253b400dc5924b731fcb42dbcd99e485200581e) | Apache-2.0 | Libre |  |
| 32 | `meta-ads` | [meta/facebook-python-business-sdk](https://github.com/meta/facebook-python-business-sdk/tree/b08e5c1d36a2adad3c4ede6578654c8eaca5f225) | LicenseRef-Meta-Platform | Libre con condición | Solo para usar con las APIs de Meta. |
| 33 | `activepieces` | [activepieces/activepieces](https://github.com/activepieces/activepieces/tree/03c15c9ce4e9cf626c9c47d7f55425556847cb19) | MIT | Libre (sin carpeta enterprise) | Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 34 | `n8n` | [n8n-io/n8n](https://github.com/n8n-io/n8n/tree/f2bbc06279d43c0d61cd474055124cb535236ba7) | SUL-1.0 | **Excluido** | Sustainable Use License: no es open source. |
| 35 | `temporal` | [temporalio/temporal](https://github.com/temporalio/temporal/tree/03ecd1d228d2b8d9d433da55785afc9aeeead918) | MIT | Libre |  |
| 36 | `trigger` | [triggerdotdev/trigger.dev](https://github.com/triggerdotdev/trigger.dev/tree/89c68810db17fefc4fe035c43fa4fcd2542db90a) | Apache-2.0 | Libre |  |
| 37 | `nango` | [NangoHQ/nango](https://github.com/NangoHQ/nango/tree/9ffe93625c309b0582108a680cd442d5aa827a97) | Elastic-2.0 | **Excluido** |  |
| 38 | `dagster` | [dagster-io/dagster](https://github.com/dagster-io/dagster/tree/93e5f51da49420d3e06d9399471070acedb554ca) | Apache-2.0 | Libre |  |
| 39 | `livekit` | [livekit/agents](https://github.com/livekit/agents/tree/59753ba7d759621ffb256b8023ebf2ddf70ffa9a) | Apache-2.0 | Libre |  |
| 40 | `pipecat` | [pipecat-ai/pipecat](https://github.com/pipecat-ai/pipecat/tree/d5dd211c15055a78431a391188e0748edd4b2661) | BSD-2-Clause | Libre |  |
| 41 | `whisper` | [openai/whisper](https://github.com/openai/whisper/tree/86098128c0b4f24f0e2aa2994de830614b474227) | MIT | Libre |  |
| 42 | `dlt` | [dlt-hub/dlt](https://github.com/dlt-hub/dlt/tree/00f21fe45e10bc77fcad53809114407c2480c851) | Apache-2.0 | Libre |  |
| 43 | `airbyte` | [airbytehq/airbyte](https://github.com/airbytehq/airbyte/tree/60fcfd2f303d1b0f472b4a337b52d7593765713b) | Elastic-2.0 | **Excluido** |  |
| 44 | `dbt` | [dbt-labs/dbt](https://github.com/dbt-labs/dbt/tree/3a3c73e46acb63bf09dbcb53ebaea1d7efdffe2e) | Apache-2.0 | Libre |  |
| 45 | `duckdb` | [duckdb/duckdb](https://github.com/duckdb/duckdb/tree/5b97627c8e0e372a4b0bade9b8a757e2c91bde33) | MIT | Libre |  |
| 46 | `clickhouse` | [ClickHouse/ClickHouse](https://github.com/ClickHouse/ClickHouse/tree/e8473460558a9f85074a90e89519a7fddb6bcacf) | Apache-2.0 | Libre |  |
| 47 | `postgres` | [postgres/postgres](https://github.com/postgres/postgres/tree/8d87367b39e44b0913ca585c733795cc2d30bff1) | PostgreSQL | Libre | Licencia PostgreSQL en el archivo COPYRIGHT. |
| 48 | `pgvector` | [pgvector/pgvector](https://github.com/pgvector/pgvector/tree/66accb3af6705ea9975a33f6704f1cde50d99447) | PostgreSQL | Libre |  |
| 49 | `qdrant` | [qdrant/qdrant](https://github.com/qdrant/qdrant/tree/222b2e44ab1c3f17e8246396ead6558e45041df7) | Apache-2.0 | Libre |  |
| 50 | `meilisearch` | [meilisearch/meilisearch](https://github.com/meilisearch/meilisearch/tree/4ef8a91f27ee6affff3f59bc46a9e07a2a761636) | MIT AND BUSL-1.1 | Libre (sin carpeta enterprise) | Núcleo MIT; módulos Enterprise Edition bajo BUSL-1.1. |
| 51 | `docling` | [docling-project/docling](https://github.com/docling-project/docling/tree/a7760abf0ca53321a3fb5ae9b1a65b584bb743b9) | MIT | Libre |  |
| 52 | `posthog` | [PostHog/posthog](https://github.com/PostHog/posthog/tree/d7ba35efef321e1c134307a67081c913aaecd219) | MIT | Libre (sin carpeta enterprise) | Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 53 | `umami` | [umami-software/umami](https://github.com/umami-software/umami/tree/559e3c607c23d2c72d9bd4f6481bda428255323c) | MIT | Libre |  |
| 54 | `plausible` | [plausible/analytics](https://github.com/plausible/analytics/tree/f7b763dd41dd62362d102393180baaf155b7b294) | AGPL-3.0 | **Excluido** |  |
| 55 | `matomo` | [matomo-org/matomo](https://github.com/matomo-org/matomo/tree/9451e9ca91ecde0fc1a86dd3c0c69391473e86a8) | GPL-3.0 | **Excluido** |  |
| 56 | `metabase` | [metabase/metabase](https://github.com/metabase/metabase/tree/0e568f5840595dcb1def7e9a08e3aa764cf4da5b) | AGPL-3.0 | **Excluido** | Carpeta enterprise bajo licencia comercial. |
| 57 | `superset` | [apache/superset](https://github.com/apache/superset/tree/4e7fa63b01ef11bd9439239bccaf670bb46a9581) | Apache-2.0 | Libre |  |
| 58 | `growthbook` | [growthbook/growthbook](https://github.com/growthbook/growthbook/tree/db1968d435056b87a9485cc78a4af3d069539405) | MIT | Libre (sin carpeta enterprise) | Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 59 | `robyn` | [facebookexperimental/Robyn](https://github.com/facebookexperimental/Robyn/tree/aab4226ed5e40196cdbd82ff7fbbff55e91e1f58) | MIT | Libre |  |
| 60 | `meridian` | [google/meridian](https://github.com/google/meridian/tree/f4ca39d406e1a86bd13d65fdf14166268044fd2d) | Apache-2.0 | Libre |  |
| 61 | `econml` | [py-why/EconML](https://github.com/py-why/EconML/tree/0b45f8343e08ebcdb93ae859643a0efe20c21e7d) | MIT | Libre |  |
| 62 | `dowhy` | [py-why/dowhy](https://github.com/py-why/dowhy/tree/b5ffe4d64a6af09437a56db77797c786dff44160) | MIT | Libre |  |
| 63 | `pymc-marketing` | [pymc-labs/pymc-marketing](https://github.com/pymc-labs/pymc-marketing/tree/4b4fead2b899dbf1982d12aab3b0cb1dfbe635fb) | Apache-2.0 | Libre |  |
| 64 | `or-tools` | [google/or-tools](https://github.com/google/or-tools/tree/100f66e6242ab8bf8d32feb8f3bf086db66ae2b5) | Apache-2.0 | Libre |  |
| 65 | `optuna` | [optuna/optuna](https://github.com/optuna/optuna/tree/9e4d3502c85cb58c3e891a48e90ef9afae00acda) | MIT | Libre |  |
| 66 | `scikit-learn` | [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn/tree/19ca9c861a7adb948a19484337159a748feede54) | BSD-3-Clause | Libre |  |
| 67 | `catboost` | [catboost/catboost](https://github.com/catboost/catboost/tree/8d797fad544091e60e830e0987e00ddf5bc3b411) | Apache-2.0 | Libre |  |
| 68 | `mlflow` | [mlflow/mlflow](https://github.com/mlflow/mlflow/tree/de4bb85d8ce26c94e4ee131b071fcc380e116ff8) | Apache-2.0 | Libre |  |
| 69 | `evidently` | [evidentlyai/evidently](https://github.com/evidentlyai/evidently/tree/34771fe41c08ca074d96a52aaf4a45cd640cbaf5) | Apache-2.0 | Libre |  |
| 70 | `great-expectations` | [fivetran/great_expectations](https://github.com/fivetran/great_expectations/tree/a3e335bf4254f77ebd92e526c0e81d6c5caa936b) | Apache-2.0 | Libre |  |
| 71 | `langgraph` | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph/tree/5ea88ecbcdb9fde713c3abd58850a5b7beaa24ec) | MIT | Libre |  |
| 72 | `pydantic-ai` | [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai/tree/21b2f46740f95a260bd492385c4638094015ec06) | MIT | Libre |  |
| 73 | `llama-index` | [run-llama/llama_index](https://github.com/run-llama/llama_index/tree/baeabbfe26241a6916e13e2a8c8156a02e0602cd) | MIT | Libre |  |
| 74 | `haystack` | [deepset-ai/haystack](https://github.com/deepset-ai/haystack/tree/bbe4efe50c716d6d05a0637980db3b641236e613) | Apache-2.0 | Libre |  |
| 75 | `langfuse` | [langfuse/langfuse](https://github.com/langfuse/langfuse/tree/72399b76e245443f9681ea93b77ca850e1edb55b) | MIT | Libre (sin carpeta enterprise) | Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 76 | `promptfoo` | [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo/tree/e5ca12a10bf4e28d8598bc800f3e4f2ad0053b2d) | MIT | Libre |  |
| 77 | `ragas` | [vibrantlabsai/ragas](https://github.com/vibrantlabsai/ragas/tree/298b68274234c060deacab3cf5fb52aa3a20e885) | Apache-2.0 | Libre |  |
| 78 | `dspy` | [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy/tree/398396012371a95471c8e7be24a70e6660e87aa4) | MIT | Libre |  |
| 79 | `bifrost` | [maximhq/bifrost](https://github.com/maximhq/bifrost/tree/ff2e69f7f0143ab79c9de5258b90bd9c70cf347b) | Apache-2.0 | Libre |  |
| 80 | `presidio` | [data-privacy-stack/presidio](https://github.com/data-privacy-stack/presidio/tree/1d7005932261a4b676e045d16fa2965dbc4b4ba2) | MIT | Libre |  |
| 81 | `medusa` | [medusajs/medusa](https://github.com/medusajs/medusa/tree/95e778ea295ca1bb672819c163738d236ce23168) | MIT | Libre (sin carpeta enterprise) | Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 82 | `saleor` | [saleor/saleor](https://github.com/saleor/saleor/tree/ea4a69fa6faa22de77a30eaee0447dd7dacaadb3) | BSD-3-Clause | Libre |  |
| 83 | `lago` | [getlago/lago](https://github.com/getlago/lago/tree/05f363fa8f3948b698137efecedb462b2d2cf333) | AGPL-3.0 | **Excluido** |  |
| 84 | `killbill` | [killbill/killbill](https://github.com/killbill/killbill/tree/52e2f55f103baf0703ddee71e10a7036595fc851) | Apache-2.0 | Libre |  |
| 85 | `openmeter` | [openmeterio/openmeter](https://github.com/openmeterio/openmeter/tree/4b7905e23bc739c43e15c4c1e09bbf9031e7cfcd) | Apache-2.0 | Libre |  |
| 86 | `better-auth` | [better-auth/better-auth](https://github.com/better-auth/better-auth/tree/262adc0e76969fe04ef9355d1c77972bd5f0a1a8) | MIT | Libre |  |
| 87 | `keycloak` | [keycloak/keycloak](https://github.com/keycloak/keycloak/tree/02167f150c0bd251f7e1e84531081c40081bcba2) | Apache-2.0 | Libre |  |
| 88 | `openfga` | [openfga/openfga](https://github.com/openfga/openfga/tree/8e4909c4ac5aa53f1915383713c07416280a7449) | Apache-2.0 | Libre |  |
| 89 | `unleash` | [Unleash/unleash](https://github.com/Unleash/unleash/tree/ecaba737eb73b90184508ffdd6344a4603dd1cfe) | AGPL-3.0 | **Excluido** |  |
| 90 | `supabase` | [supabase/supabase](https://github.com/supabase/supabase/tree/f38928ad90f1c2bd44f668411fb1d2312754d258) | Apache-2.0 | Libre |  |
| 91 | `coolify` | [coollabsio/coolify](https://github.com/coollabsio/coolify/tree/d9ab3d1e8bea98215ed19a27f2f4ac1abd2fa40f) | Apache-2.0 | Libre |  |
| 92 | `grafana` | [grafana/grafana](https://github.com/grafana/grafana/tree/3a858269421f77d107c876f60ce14f8b7aabe5c5) | AGPL-3.0 | **Excluido** |  |
| 93 | `prometheus` | [prometheus/prometheus](https://github.com/prometheus/prometheus/tree/49c815a0ea46c7a6a6b723e4b634c4bf36f7022c) | Apache-2.0 | Libre |  |
| 94 | `otel-collector` | [open-telemetry/opentelemetry-collector](https://github.com/open-telemetry/opentelemetry-collector/tree/e366bb7fb49a67fd117332fff93795a0050744ff) | Apache-2.0 | Libre |  |
| 95 | `sops` | [getsops/sops](https://github.com/getsops/sops/tree/9aa10f12bcd82400b7eb73331dd7a87a93bb17f7) | MPL-2.0 | Libre con condición | MPL-2.0: si modificas sus archivos, esos archivos se comparten. |
| 96 | `infisical` | [Infisical/infisical](https://github.com/Infisical/infisical/tree/09079738070ecc82e17a150f223226eb4f6647d8) | MIT | Libre (sin carpeta enterprise) | Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 97 | `grype` | [anchore/grype](https://github.com/anchore/grype/tree/cd1f23eb50dfb52647090158f453c7359172591f) | Apache-2.0 | Libre |  |
| 98 | `syft` | [anchore/syft](https://github.com/anchore/syft/tree/a0c0d3890a9d79421c403e8fcadec50a2e55bf21) | Apache-2.0 | Libre |  |
| 99 | `gitleaks` | [gitleaks/gitleaks](https://github.com/gitleaks/gitleaks/tree/5f6ec56cfa6f8c67648d863582c7ae2f206d5c1c) | MIT | Libre |  |
| 100 | `restic` | [restic/restic](https://github.com/restic/restic/tree/c734245fd3ae9bcac8ab3aaafb4482d4b5d0ae92) | BSD-2-Clause | Libre |  |

## Tus 50 originales (los que pasaron el filtro y no estaban ya en el núcleo) (21)

| # | ID | Repositorio | Licencia | Política | Nota |
|---|---|---|---|---|---|
| 101 | `openprospector` | [clawnify/OpenProspector](https://github.com/clawnify/OpenProspector/tree/dad0e778ff4e1438b69574ff9cbb7663a3bda6e6) | MIT | Libre |  |
| 102 | `langflow` | [langflow-ai/langflow](https://github.com/langflow-ai/langflow/tree/260cbf347cc5563cc48c79094c175ca31532ea2b) | MIT | Libre |  |
| 103 | `openrefine` | [OpenRefine/OpenRefine](https://github.com/OpenRefine/OpenRefine/tree/d97abdabd4c172ddba3581a9259307c7f2b86b44) | BSD-3-Clause | Libre |  |
| 104 | `openseo` | [duckduckdeploy/openseo](https://github.com/duckduckdeploy/openseo/tree/12b525400539f980668d088ff7154236a2376e88) | MIT | Libre |  |
| 105 | `mcp-gsc` | [AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc/tree/45291df024c7873b2042c83d7add70ced7bb621f) | MIT | Libre |  |
| 106 | `siteone-crawler` | [janreges/siteone-crawler](https://github.com/janreges/siteone-crawler/tree/f3d967b190a77ff5f816b7ddab74c1a778d9dbaf) | MIT | Libre |  |
| 107 | `advertools` | [eliasdabbas/advertools](https://github.com/eliasdabbas/advertools/tree/59dc2be7a98ab3bab2a711efacd5023f8ecffa14) | MIT | Libre |  |
| 108 | `cal-diy` | [calcom/cal.diy](https://github.com/calcom/cal.diy/tree/ae027bb70e694e2d2c44569f398d6cbcee0389b1) | MIT | Libre |  |
| 109 | `uptime-kuma` | [louislam/uptime-kuma](https://github.com/louislam/uptime-kuma/tree/4f6661cfa83a06be0353d5536ef3d9ee0064f534) | MIT | Libre |  |
| 110 | `opengmb` | [synectus/OpenGMB](https://github.com/synectus/OpenGMB/tree/8f399472e9d484cfcad77eef33b0da341e469577) | MIT | Libre |  |
| 111 | `kingfisher-collect` | [open-contracting/kingfisher-collect](https://github.com/open-contracting/kingfisher-collect/tree/865bbb20ff4e6495bd2aba08bef5f2a0a1a648f6) | BSD-3-Clause | Libre |  |
| 112 | `markitdown` | [microsoft/markitdown](https://github.com/microsoft/markitdown/tree/ed178952a6672abdfd35b5f9e76a80b6cefc086e) | MIT | Libre |  |
| 113 | `spacy` | [explosion/spaCy](https://github.com/explosion/spaCy/tree/7ff14d4da84817f84c32b980882178ddacc066a1) | MIT | Libre |  |
| 114 | `schema-dts` | [google/schema-dts](https://github.com/google/schema-dts/tree/0dc1d1f518af5a727ada9d162c714ddf74710686) | Apache-2.0 | Libre |  |
| 115 | `web-vitals` | [GoogleChrome/web-vitals](https://github.com/GoogleChrome/web-vitals/tree/94b3b4bced9d63b4ff6bfb8290bf1f505daa00bb) | Apache-2.0 | Libre |  |
| 116 | `altcha` | [altcha-org/altcha](https://github.com/altcha-org/altcha/tree/5691046ab911524f7c8e0e6a01609c15fd5a2299) | MIT | Libre |  |
| 117 | `cookieconsent` | [orestbida/cookieconsent](https://github.com/orestbida/cookieconsent/tree/e0a3fe118d90c1c430ca9dfcd03aca531bce3dc5) | MIT | Libre |  |
| 118 | `libphonenumber` | [google/libphonenumber](https://github.com/google/libphonenumber/tree/981600cc587fb87483ad294a61daa187afc64b2c) | Apache-2.0 | Libre |  |
| 119 | `twilio-python` | [twilio/twilio-python](https://github.com/twilio/twilio-python/tree/7e3ca781178dcaa542b403591a58e5bc58b874a8) | MIT | Libre |  |
| 120 | `stripe-python` | [stripe/stripe-python](https://github.com/stripe/stripe-python/tree/7254286570dcacb689f933db913e7cdf303818db) | MIT | Libre |  |
| 121 | `parsedmarc` | [domainaware/parsedmarc](https://github.com/domainaware/parsedmarc/tree/70a0ea0470d04649e33e6b09ce20da991d424f72) | Apache-2.0 | Libre |  |

## Marketing de autoridad (43)

| # | ID | Repositorio | Licencia | Política | Nota |
|---|---|---|---|---|---|
| 122 | `geo-optimizer` | [Auriti-Labs/geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill/tree/b7fd7dfaaeb9a28841954ac373236211813ca5f2) | MIT | Libre |  |
| 123 | `geo-lint` | [IJONIS/geo-lint](https://github.com/IJONIS/geo-lint/tree/b2d79319d1d0d4d4fc5d6abbc4ce5156afc5d14b) | MIT | Libre |  |
| 124 | `autogeo` | [cxcscmu/AutoGEO](https://github.com/cxcscmu/AutoGEO/tree/49456df236774ea24087c44f45e9e52005b8e6a4) | MIT | Libre |  |
| 125 | `site-md` | [yazinsai/site-md](https://github.com/yazinsai/site-md/tree/c5c31bc781d06f83a81d30a284f0df3aa2ffbe32) | MIT | Libre |  |
| 126 | `nlweb` | [microsoft/NLWeb](https://github.com/microsoft/NLWeb/tree/b423f15d9aeaa023ce75993ac9deed2354597043) | MIT | Libre |  |
| 127 | `goaccess` | [allinurl/goaccess](https://github.com/allinurl/goaccess/tree/6e890b584b8b36c445aa37dea83d7d5519d5fc46) | MIT | Libre |  |
| 128 | `ipranges` | [lord-alfred/ipranges](https://github.com/lord-alfred/ipranges/tree/d4ea6c582a509538907480e641bcee6821746bc3) | CC0-1.0 | Libre |  |
| 129 | `anubis` | [TecharoHQ/anubis](https://github.com/TecharoHQ/anubis/tree/f197f9a6235d255000c7b654ac478354a6e4bd02) | MIT | Libre |  |
| 130 | `the-great-gpt-firewall` | [samber/the-great-gpt-firewall](https://github.com/samber/the-great-gpt-firewall/tree/60b2214d7b2cbd2c1b9d175afb31ad3024c085bb) | MIT | Libre |  |
| 131 | `seo-graph` | [jdevalk/seo-graph](https://github.com/jdevalk/seo-graph/tree/c33eb1e120c620970042e28f1332fc90c30125e6) | MIT | Libre |  |
| 132 | `structured-data-validator` | [adobe/structured-data-validator](https://github.com/adobe/structured-data-validator/tree/6918b52651d6f4c5dae612859e2e395de5a1910e) | Apache-2.0 | Libre |  |
| 133 | `pywikibot` | [wikimedia/pywikibot](https://github.com/wikimedia/pywikibot/tree/b8ccec48b3c26211cd498e27a5ca6eb071627cb1) | MIT | Libre |  |
| 134 | `id-openstreetmap` | [openstreetmap/iD](https://github.com/openstreetmap/iD/tree/ae5315e584f0df10cace683ec1032140e5a38204) | ISC | Libre |  |
| 135 | `sherlock` | [sherlock-project/sherlock](https://github.com/sherlock-project/sherlock/tree/c588d7c8b476df9f9c84912a05d1430fb8cdcdae) | MIT | Libre |  |
| 136 | `indexnow-for-python` | [jakob-bagterp/index-now-for-python](https://github.com/jakob-bagterp/index-now-for-python/tree/47e9f82412e95a55b2c177ca66d79786117349c6) | MIT | Libre |  |
| 137 | `feed` | [jpmonette/feed](https://github.com/jpmonette/feed/tree/cbad18d8afb6ea9fc38d460fdf56a2713c313aed) | MIT | Libre |  |
| 138 | `cdx-toolkit` | [cocrawler/cdx_toolkit](https://github.com/cocrawler/cdx_toolkit/tree/e87b1204993b77a4c41c03239baefa1c8462a6e1) | Apache-2.0 | Libre |  |
| 139 | `cc-webgraph` | [commoncrawl/cc-webgraph](https://github.com/commoncrawl/cc-webgraph/tree/8a3a34e2f3bc16b865ee234eab83a4917086b814) | Apache-2.0 | Libre |  |
| 140 | `trendspyg` | [flack0x/trendspyg](https://github.com/flack0x/trendspyg/tree/9f07b2573e7287df85df9202da206569024723e9) | MIT | Libre |  |
| 141 | `waybackpy` | [akamhy/waybackpy](https://github.com/akamhy/waybackpy/tree/3b3e78d901a600bb22943202c6a8981ca04a5e48) | MIT | Libre |  |
| 142 | `newsjack` | [elvisun/newsjack](https://github.com/elvisun/newsjack/tree/c2df3a0168083d620b9b36518aeca16a4eb72296) | MIT | Libre |  |
| 143 | `gdeltdoc` | [alex9smith/gdelt-doc-api](https://github.com/alex9smith/gdelt-doc-api/tree/41220163fbab99982e4dca3a05d25a95b49896d7) | MIT | Libre |  |
| 144 | `news-please` | [fhamborg/news-please](https://github.com/fhamborg/news-please/tree/f899850be2bb0059da101c13502ec88af057f974) | Apache-2.0 | Libre |  |
| 145 | `python-podcastindex` | [piqosoft/python-podcastindex](https://github.com/piqosoft/python-podcastindex/tree/63fdb84b76b5d65c99e9c92428af55cc51aff04e) | MIT | Libre |  |
| 146 | `praw` | [praw-dev/praw](https://github.com/praw-dev/praw/tree/4590cb5b0ad2f9afbab983d60d792fc3c74d1f45) | BSD-2-Clause | Libre |  |
| 147 | `youtube-comment-downloader` | [egbertbouman/youtube-comment-downloader](https://github.com/egbertbouman/youtube-comment-downloader/tree/3f557bc8023d9e3ab9edda93bcd516ca2b33d3c1) | MIT | Libre |  |
| 148 | `people-also-ask` | [labsonmars/people_also_ask](https://github.com/labsonmars/people_also_ask/tree/21db28fb5a75d233bf18db381fab538791eee495) | MIT | Libre |  |
| 149 | `google-maps-scraper` | [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper/tree/e0c1d501e49cdcd5c6b2cecd2a032831f6ee9ba8) | MIT | Libre |  |
| 150 | `dnstwist` | [elceef/dnstwist](https://github.com/elceef/dnstwist/tree/341395377f40761fe4152f43fd18eea757b6069a) | Apache-2.0 | Libre |  |
| 151 | `c2pa` | [contentauth/c2pa-rs](https://github.com/contentauth/c2pa-rs/tree/0e92435c6d621c02c9bde2a8d82346295ed1f509) | Apache-2.0 OR MIT | Libre |  |
| 152 | `vale` | [errata-ai/vale](https://github.com/errata-ai/vale/tree/4ce91ef208b37f9ac2894766e8cd7b33ffe3baed) | MIT | Libre |  |
| 153 | `datasette` | [simonw/datasette](https://github.com/simonw/datasette/tree/32590d8f32244d922ee1f444e432fb48b11ce05b) | Apache-2.0 | Libre |  |
| 154 | `ckanapi` | [ckan/ckanapi](https://github.com/ckan/ckanapi/tree/94b8c24a21a185c270a01bcbcfa72ff4e1b78b1c) | MIT | Libre |  |
| 155 | `quarto` | [quarto-dev/quarto-cli](https://github.com/quarto-dev/quarto-cli/tree/1782b5b3099e8e4dd62cf7bac590d3bad2072c56) | MIT | Libre |  |
| 156 | `owncast` | [owncast/owncast](https://github.com/owncast/owncast/tree/c3a9ac1c46c043358fe7382a6d62d5227e4b2efe) | MIT | Libre |  |
| 157 | `auto-editor` | [WyattBlue/auto-editor](https://github.com/WyattBlue/auto-editor/tree/2bbdcd95bc221254e4e6e00eb4c827b06ae93f71) | Unlicense | Libre |  |
| 158 | `slidev` | [slidevjs/slidev](https://github.com/slidevjs/slidev/tree/437f139ccd4c8482a193b217922e7800a5b3baec) | MIT | Libre |  |
| 159 | `carousel-generator` | [FranciscoMoretti/carousel-generator](https://github.com/FranciscoMoretti/carousel-generator/tree/4bc98958a038717775c1b1d57124b8a6b0095f9a) | MIT | Libre |  |
| 160 | `excalidraw` | [excalidraw/excalidraw](https://github.com/excalidraw/excalidraw/tree/82d5847e57dcb6fb5982833ea9ec2137fe0b2bd5) | MIT | Libre |  |
| 161 | `apache-answer` | [apache/answer](https://github.com/apache/answer/tree/6744295fa888e0621fc9f9a8ace04f1a4daf8554) | Apache-2.0 | Libre |  |
| 162 | `local-seo-skills` | [garrettjsmith/localseoskills](https://github.com/garrettjsmith/localseoskills/tree/c3b7a25b7d5cc370752d74cfea240ccf992a24db) | MIT | Libre |  |
| 163 | `a2a` | [a2aproject/A2A](https://github.com/a2aproject/A2A/tree/4d7cda4b1754ed410e41bf3be7ad9ebc62afe3d3) | Apache-2.0 | Libre |  |
| 164 | `webmention-io` | [aaronpk/webmention.io](https://github.com/aaronpk/webmention.io/tree/9183deed829c2399e6cd7f594ab8f1d84492e86b) | BSD (declarada en README) | Libre con condición | Licencia declarada solo en el README. |

## Estrategia de negocio (36)

| # | ID | Repositorio | Licencia | Política | Nota |
|---|---|---|---|---|---|
| 165 | `claude-skills-c-level` | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills/tree/08cd8a9fc86cc370e2c0d448e8171fbcfdbc5a30) | MIT | Libre |  |
| 166 | `tinytroupe` | [microsoft/TinyTroupe](https://github.com/microsoft/TinyTroupe/tree/7ce8be378a37ee73f9745d6781452712318afa04) | MIT | Libre |  |
| 167 | `gpt-researcher` | [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher/tree/ddd4db36208d9c8e49f3b2436efda97baecb5433) | Apache-2.0 | Libre |  |
| 168 | `forecasting-tools` | [Metaculus/forecasting-tools](https://github.com/Metaculus/forecasting-tools/tree/bd7e6a65e7f01141af8cab411ff8f51f908f8061) | MIT | Libre |  |
| 169 | `onlinewardleymaps` | [damonsk/onlinewardleymaps](https://github.com/damonsk/onlinewardleymaps/tree/71f2aad88ae83862fdce27c55c6733b8ba1009aa) | MIT | Libre |  |
| 170 | `operately` | [operately/operately](https://github.com/operately/operately/tree/9fa8692fb61cec13730fb4523daf57c29261be45) | Apache-2.0 | Libre (sin carpeta enterprise) | Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 171 | `bpmn-js` | [bpmn-io/bpmn-js](https://github.com/bpmn-io/bpmn-js/tree/b3f1c4837d9ed2f624af9b7a6bcfe5da7f6eeac8) | MIT | Libre |  |
| 172 | `landscape-app` | [cncf/landscapeapp](https://github.com/cncf/landscapeapp/tree/a882d0675b2cd9ace3fa158f6d8df3b65a5a82cf) | Apache-2.0 | Libre |  |
| 173 | `datosmex` | [andreslomeliv/DatosMex](https://github.com/andreslomeliv/DatosMex/tree/4179265209ca8345cc2de533f82612a6ca45314f) | MIT | Libre | MIT en las subcarpetas BANXICOpy e INEGIpy. |
| 174 | `wbgapi` | [tgherzog/wbgapi](https://github.com/tgherzog/wbgapi/tree/4d0d2c925a8dac359df5a2d9e82001ff6feeecda) | MIT | Libre |  |
| 175 | `census` | [datamade/census](https://github.com/datamade/census/tree/3da5a1068164c27f6e83815f5d28ec300e184fdf) | BSD-3-Clause | Libre |  |
| 176 | `comtradeapicall` | [uncomtrade/comtradeapicall](https://github.com/uncomtrade/comtradeapicall/tree/d8b19588986405df8c3c94062bd73fd08b9110cd) | MIT | Libre |  |
| 177 | `py-ecomplexity` | [cid-harvard/py-ecomplexity](https://github.com/cid-harvard/py-ecomplexity/tree/d22c0f7fcad4cf629415895dd17afc5685108274) | MIT | Libre |  |
| 178 | `openbb` | [OpenBB-finance/OpenBB](https://github.com/OpenBB-finance/OpenBB/tree/e43353a82815ff9ba56ad1b7ad47c32729dcf314) | Apache-2.0 | Libre |  |
| 179 | `financetoolkit` | [JerBouma/FinanceToolkit](https://github.com/JerBouma/FinanceToolkit/tree/375f820d8f84e90e2f42f5d413ed67056cbd4256) | MIT | Libre |  |
| 180 | `jobspy` | [speedyapply/JobSpy](https://github.com/speedyapply/JobSpy/tree/68b88d6909a2342ad75fbb945c4204a3a7ed6665) | MIT | Libre |  |
| 181 | `osmnx` | [gboeing/osmnx](https://github.com/gboeing/osmnx/tree/5f3b46f048f9f0a693702cea5f29f2eaad840204) | MIT | Libre |  |
| 182 | `kepler-gl` | [keplergl/kepler.gl](https://github.com/keplergl/kepler.gl/tree/89954d5ed8fea6fb829f317a488f5b553bf34c24) | MIT | Libre |  |
| 183 | `taguette` | [remram44/taguette](https://github.com/remram44/taguette/tree/52fcdce95709375a4085cb10852bf7dd251ccb3d) | BSD-3-Clause | Libre |  |
| 184 | `bertopic` | [MaartenGr/BERTopic](https://github.com/MaartenGr/BERTopic/tree/9036123c97aaa9a6cc4bec4a6db1a7caf9209df6) | MIT | Libre |  |
| 185 | `pricesensitivitymeter` | [max-alletsee/pricesensitivitymeter](https://github.com/max-alletsee/pricesensitivitymeter/tree/8188de1e95fa0f407073677f6f88baec2f43c8d4) | MIT | Libre | Licencia MIT de R (archivo corto con año y titular). |
| 186 | `squiggle` | [quantified-uncertainty/squiggle](https://github.com/quantified-uncertainty/squiggle/tree/87e04dabcf9e50ceadd6abcd297aad145c999045) | MIT | Libre |  |
| 187 | `statsforecast` | [Nixtla/statsforecast](https://github.com/Nixtla/statsforecast/tree/652a4e940f4f7993d894cdff74ac6ec9a5f01247) | Apache-2.0 | Libre |  |
| 188 | `statsmodels` | [statsmodels/statsmodels](https://github.com/statsmodels/statsmodels/tree/27e747596049cc1a9b06e113af739fdeec59cecc) | BSD-3-Clause | Libre |  |
| 189 | `mlxtend` | [rasbt/mlxtend](https://github.com/rasbt/mlxtend/tree/1aee767ef57b84a8191511a08955c583b65de382) | BSD-3-Clause | Libre | Código BSD-3; documentación CC-BY. |
| 190 | `networkx` | [networkx/networkx](https://github.com/networkx/networkx/tree/6855cd586982cc2e4710b8eb87251ccf56674bf1) | BSD-3-Clause | Libre |  |
| 191 | `pymcdm` | [kotbaton/pymcdm](https://github.com/kotbaton/pymcdm/tree/346a44f5afdac249c534912cc8d483e82586c52d) | MIT | Libre |  |
| 192 | `nashpy` | [drvinceknight/Nashpy](https://github.com/drvinceknight/Nashpy/tree/a797cfd91e065f1ac67f9660b27d487627ec5528) | MIT | Libre |  |
| 193 | `mesa` | [projectmesa/mesa](https://github.com/projectmesa/mesa/tree/2d9b25177627f38fb43c4273ac2bdd03b95f01cb) | Apache-2.0 | Libre |  |
| 194 | `pysd` | [SDXorg/pysd](https://github.com/SDXorg/pysd/tree/8991d119e139029d4dec712d257cf5fcc3549b8f) | MIT | Libre |  |
| 195 | `numpy-financial` | [numpy/numpy-financial](https://github.com/numpy/numpy-financial/tree/031ed55d322b7aad57311b9d63b589c79df942a1) | BSD-3-Clause | Libre |  |
| 196 | `graphrag` | [microsoft/graphrag](https://github.com/microsoft/graphrag/tree/34b2b67ae4601ad0b47bcd179fbe3f2a23aa0857) | MIT | Libre |  |
| 197 | `vanna` | [vanna-ai/vanna](https://github.com/vanna-ai/vanna/tree/365d0617c1a4567ffee1b19b40c27feb4206bfcf) | MIT | Libre |  |
| 198 | `marimo` | [marimo-team/marimo](https://github.com/marimo-team/marimo/tree/9bdfb7605fe75aebd74ce909b83c3cbd743bd23d) | Apache-2.0 | Libre |  |
| 199 | `grist` | [gristlabs/grist-core](https://github.com/gristlabs/grist-core/tree/a3c557ac1bc4bd55b9b9d4333842bec255586ff4) | Apache-2.0 | Libre |  |
| 200 | `log4brains` | [thomvaill/log4brains](https://github.com/thomvaill/log4brains/tree/17e32021a8c5130386f17e921d4efa6da7709a66) | Apache-2.0 | Libre |  |

## Bloque 4 — Agentes autónomos (40)

| # | ID | Repositorio | Licencia | Política | Nota |
|---|---|---|---|---|---|
| 201 | `crewai` | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI/tree/d7dfa0ef5ade793bd48ff7357c6eb45a45294371) | MIT | Libre |  |
| 202 | `openai-agents` | [openai/openai-agents-python](https://github.com/openai/openai-agents-python/tree/64fbde5d02b42ae5f9db668eb0184cdb3fc9d775) | MIT | Libre |  |
| 203 | `google-adk` | [google/adk-python](https://github.com/google/adk-python/tree/12aab4aaaa1a72e3edcc65fa4f9d849896ea6c48) | Apache-2.0 | Libre |  |
| 204 | `agent-framework` | [microsoft/agent-framework](https://github.com/microsoft/agent-framework/tree/92838b60498395142cb8b74693353163e95a0faf) | MIT | Libre |  |
| 205 | `smolagents` | [huggingface/smolagents](https://github.com/huggingface/smolagents/tree/96f33faaf028479119ec8d34507b47694cf14e34) | Apache-2.0 | Libre |  |
| 206 | `camel` | [camel-ai/camel](https://github.com/camel-ai/camel/tree/0366b64bf3609c76f50e396715aab73ba58a930c) | Apache-2.0 | Libre |  |
| 207 | `mastra` | [mastra-ai/mastra](https://github.com/mastra-ai/mastra/tree/7277766d6c967c475675d58ff2d0e5c6d7be7c84) | Apache-2.0 | Libre (sin carpeta enterprise) | Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 208 | `any-agent` | [mozilla-ai/any-agent](https://github.com/mozilla-ai/any-agent/tree/a469723ac4a0518ab0696d57e09e4dc407c826ec) | Apache-2.0 | Libre |  |
| 209 | `langchain` | [langchain-ai/langchain](https://github.com/langchain-ai/langchain/tree/ea17e48f0a4336c920394fd029de99f1568b4c38) | MIT | Libre |  |
| 210 | `langgraph-supervisor` | [langchain-ai/langgraph-supervisor-py](https://github.com/langchain-ai/langgraph-supervisor-py/tree/88859b34017ac3569bbd4a3092c7e77593a0a960) | MIT | Libre |  |
| 211 | `letta` | [letta-ai/letta](https://github.com/letta-ai/letta/tree/8816d3a8516893bfdc0fa14bfb1235226012e295) | Apache-2.0 | Libre |  |
| 212 | `mem0` | [mem0ai/mem0](https://github.com/mem0ai/mem0/tree/f1791daa86d469249c9b002f62644d58a1eb96a0) | Apache-2.0 | Libre |  |
| 213 | `graphiti` | [getzep/graphiti](https://github.com/getzep/graphiti/tree/3ed02527499d4eb3b2eb133d716898dc89d7cc99) | Apache-2.0 | Libre |  |
| 214 | `browser-use` | [browser-use/browser-use](https://github.com/browser-use/browser-use/tree/480d0bd508ce10dcf27a4716f2f87355a08e8372) | MIT | Libre |  |
| 215 | `stagehand` | [browserbase/stagehand](https://github.com/browserbase/stagehand/tree/6f2686d792b7f5836b04754e0f6a44db39928592) | MIT | Libre |  |
| 216 | `playwright-mcp` | [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp/tree/78eca85361efb545a4c0f59b6140aef0721c5412) | Apache-2.0 | Libre |  |
| 217 | `mcp-python-sdk` | [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk/tree/77001c96f9507be0f4d009b83210a384a5e08bda) | MIT | Libre |  |
| 218 | `mcp-typescript-sdk` | [modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk/tree/919bb8ea88b6e10e72c2f8b6218fad4cfdc40b2c) | Apache-2.0 | Libre | En transición de MIT a Apache-2.0. |
| 219 | `fastmcp` | [PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp/tree/a8745d61e650467756bb28b4157822dbfbdfa34f) | Apache-2.0 | Libre |  |
| 220 | `mcp-agent` | [lastmile-ai/mcp-agent](https://github.com/lastmile-ai/mcp-agent/tree/f62d849350816588b1c6294e7914bbe4d8b84072) | Apache-2.0 | Libre |  |
| 221 | `e2b` | [e2b-dev/E2B](https://github.com/e2b-dev/E2B/tree/6dc8d5a10aa5db8dc8cf9c4d95fc769d886197fd) | Apache-2.0 | Libre |  |
| 222 | `guardrails` | [guardrails-ai/guardrails](https://github.com/guardrails-ai/guardrails/tree/06d0ff2c5f9bcb493d976b76f885e37e41ce845d) | Apache-2.0 | Libre |  |
| 223 | `nemo-guardrails` | [NVIDIA/NeMo-Guardrails](https://github.com/NVIDIA/NeMo-Guardrails/tree/5d7f4c1ca62fb6155066e6c581379d1a5ec11338) | Apache-2.0 | Libre |  |
| 224 | `instructor` | [567-labs/instructor](https://github.com/567-labs/instructor/tree/2549049be07ec3be1d617f8904ea8ffe18253c48) | MIT | Libre |  |
| 225 | `outlines` | [dottxt-ai/outlines](https://github.com/dottxt-ai/outlines/tree/c52af8472c6fe8a607a733ec11b709476af77a96) | Apache-2.0 | Libre |  |
| 226 | `ollama` | [ollama/ollama](https://github.com/ollama/ollama/tree/a5864fcb33969705de3c0ebfedf4b2a16c970bcc) | MIT | Libre |  |
| 227 | `vllm` | [vllm-project/vllm](https://github.com/vllm-project/vllm/tree/37ea94f715acc34f84bc3728ec3e365e40eb53ac) | Apache-2.0 | Libre |  |
| 228 | `openhands` | [All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands/tree/685eb42ded117ba0321aa8c3019e6677e5474317) | MIT | Libre |  |
| 229 | `storm` | [stanford-oval/storm](https://github.com/stanford-oval/storm/tree/fb951af7744dab086e34962e9bc6fe878e145f83) | MIT | Libre |  |
| 230 | `magentic-ui` | [microsoft/magentic-ui](https://github.com/microsoft/magentic-ui/tree/d3c9d13c39288257286a66daabf7c5b5fb72ee69) | MIT | Libre |  |
| 231 | `humanlayer` | [humanlayer/humanlayer](https://github.com/humanlayer/humanlayer/tree/b7ad8e1d383ff0f5fbec7bdc30425e4a59d5f789) | Apache-2.0 | Libre |  |
| 232 | `cua` | [trycua/cua](https://github.com/trycua/cua/tree/c372e5fb2bae944974e903fbf117c61f4ced696e) | MIT | Libre |  |
| 233 | `composio` | [ComposioHQ/composio](https://github.com/ComposioHQ/composio/tree/fdee7595166f8b5dcff026dc609760d1ce82b2e2) | MIT | Libre |  |
| 234 | `ag-ui` | [ag-ui-protocol/ag-ui](https://github.com/ag-ui-protocol/ag-ui/tree/0fc064bb2647fc0bce4fc795af33b5551ac03f88) | MIT | Libre |  |
| 235 | `copilotkit` | [CopilotKit/CopilotKit](https://github.com/CopilotKit/CopilotKit/tree/7b88608455528bd2dd62752a01cc25b8c917d35c) | MIT | Libre |  |
| 236 | `vercel-ai-sdk` | [vercel/ai](https://github.com/vercel/ai/tree/0e8e0543aeda7d4dd4ce6eade0d5b7d5a43644c1) | Apache-2.0 | Libre |  |
| 237 | `assistant-ui` | [assistant-ui/assistant-ui](https://github.com/assistant-ui/assistant-ui/tree/7d7427653f6ba47b0b954510eed9c594d64e74d5) | MIT | Libre |  |
| 238 | `steel-browser` | [steel-dev/steel-browser](https://github.com/steel-dev/steel-browser/tree/552550af79742a75fef24c24b1134e43e99e3d5e) | Apache-2.0 | Libre |  |
| 239 | `llm-guard` | [protectai/llm-guard](https://github.com/protectai/llm-guard/tree/168c1034ffdb33837e7ae6fd6a16b80567c1be03) | MIT | Libre |  |
| 240 | `a2a-python` | [a2aproject/a2a-python](https://github.com/a2aproject/a2a-python/tree/09c93473a77d0a18be8429ad71958211b736a8c0) | Apache-2.0 | Libre |  |

## Bloque 5 — Plataforma de producto (40)

| # | ID | Repositorio | Licencia | Política | Nota |
|---|---|---|---|---|---|
| 241 | `trpc` | [trpc/trpc](https://github.com/trpc/trpc/tree/1283c63af31aab98bda30fb6168e753480c7d455) | MIT | Libre |  |
| 242 | `hono` | [honojs/hono](https://github.com/honojs/hono/tree/f6fbaf0299c48eea9e656e03e2ffe7ac755e8823) | MIT | Libre |  |
| 243 | `fastapi` | [fastapi/fastapi](https://github.com/fastapi/fastapi/tree/5758a9c8347d911444dca97a55b708cc4a8de4f8) | MIT | Libre |  |
| 244 | `drizzle` | [drizzle-team/drizzle-orm](https://github.com/drizzle-team/drizzle-orm/tree/3bcb6a27ec1f4f1602aeeb0af2f5aec61010d72d) | Apache-2.0 | Libre |  |
| 245 | `nextjs` | [vercel/next.js](https://github.com/vercel/next.js/tree/cbd8159c02ea96064457f7b654bbb9d4eab45137) | MIT | Libre |  |
| 246 | `shadcn-ui` | [shadcn-ui/ui](https://github.com/shadcn-ui/ui/tree/e62c9435fff729a175f38983dee73b2cb4f6a069) | MIT | Libre |  |
| 247 | `tailwindcss` | [tailwindlabs/tailwindcss](https://github.com/tailwindlabs/tailwindcss/tree/b08bf83a327271dfb7e3cd485fd793da15013f7c) | MIT | Libre |  |
| 248 | `refine` | [refinedev/refine](https://github.com/refinedev/refine/tree/2352eb5b6539e2f39ad9aef652279ad1dcf2c467) | MIT | Libre |  |
| 249 | `echarts` | [apache/echarts](https://github.com/apache/echarts/tree/34f4d927eafe251f26f63afd3aeefa30f2feba30) | Apache-2.0 | Libre |  |
| 250 | `tanstack-query` | [TanStack/query](https://github.com/TanStack/query/tree/36dd7927c85ce6cee37ab1eb3af25e7fc7ccbb14) | MIT | Libre |  |
| 251 | `tanstack-table` | [TanStack/table](https://github.com/TanStack/table/tree/c14e0221b1e656c7bb35e7b3d4cdf188719a3599) | MIT | Libre |  |
| 252 | `i18next` | [i18next/i18next](https://github.com/i18next/i18next/tree/cc3b9853828b1e1fb17d20d176ee9c161e97a348) | MIT | Libre |  |
| 253 | `seaweedfs` | [seaweedfs/seaweedfs](https://github.com/seaweedfs/seaweedfs/tree/e0890391acff2e8cac6dea79c28e931ab1dfb70e) | Apache-2.0 | Libre |  |
| 254 | `caddy` | [caddyserver/caddy](https://github.com/caddyserver/caddy/tree/7591cff1fb03202ce022982af020197f3f387220) | Apache-2.0 | Libre |  |
| 255 | `openapi-generator` | [OpenAPITools/openapi-generator](https://github.com/OpenAPITools/openapi-generator/tree/1d942536cd430bd303076e0eef28325cc6e965fe) | Apache-2.0 | Libre |  |
| 256 | `scalar` | [scalar/scalar](https://github.com/scalar/scalar/tree/252a3ada30e3fcd92e88756b4ccb1c4a9c8f09fa) | MIT | Libre |  |
| 257 | `starlight` | [withastro/starlight](https://github.com/withastro/starlight/tree/62821331b95d55e9346ca34ebacc676d7be1f26b) | MIT | Libre |  |
| 258 | `svix` | [svix/svix-webhooks](https://github.com/svix/svix-webhooks/tree/bb44d9a55f2bd409cb502d8bdab6b2e28710846c) | MIT | Libre |  |
| 259 | `bullmq` | [taskforcesh/bullmq](https://github.com/taskforcesh/bullmq/tree/c9c13438716597e1d2e4d5eeb276a9ce88d12750) | MIT | Libre |  |
| 260 | `valkey` | [valkey-io/valkey](https://github.com/valkey-io/valkey/tree/c98c0e2e6c271a24c829d17b2ed94d64c576c33f) | BSD-3-Clause | Libre |  |
| 261 | `tusd` | [tus/tusd](https://github.com/tus/tusd/tree/cec39980890809a9e7202872ec32f736f3b4a3f5) | MIT | Libre |  |
| 262 | `uppy` | [transloadit/uppy](https://github.com/transloadit/uppy/tree/25c2f434932d1ecb2942efad81eff1969a79c85b) | MIT | Libre |  |
| 263 | `sharp` | [lovell/sharp](https://github.com/lovell/sharp/tree/80323211e23afa4f56d63c70e7db17dfd6e588f0) | Apache-2.0 | Libre |  |
| 264 | `surveyjs` | [surveyjs/survey-library](https://github.com/surveyjs/survey-library/tree/5f275a7d8daa4ae5a499c5d5302964474fd78e62) | MIT | Libre |  |
| 265 | `tiptap` | [ueberdosis/tiptap](https://github.com/ueberdosis/tiptap/tree/93574965bafd2f5067fd59238920595ecc3fa33b) | MIT | Libre |  |
| 266 | `gotenberg` | [gotenberg/gotenberg](https://github.com/gotenberg/gotenberg/tree/4d577e1467aaffa080b1e89d64ecb86c2fba4e98) | MIT | Libre |  |
| 267 | `signoz` | [SigNoz/signoz](https://github.com/SigNoz/signoz/tree/ca7daf8ea974b879379101c7f7d8cb420da6acc7) | MIT | Libre (sin carpeta enterprise) | Núcleo libre; no usar carpetas o archivos enterprise/comerciales. |
| 268 | `expo` | [expo/expo](https://github.com/expo/expo/tree/696b087dc08f27e0836409f4a736679bcbde194f) | MIT | Libre |  |
| 269 | `hoppscotch` | [hoppscotch/hoppscotch](https://github.com/hoppscotch/hoppscotch/tree/55908a76a1d0555c9bbb5d74244c14173df95b06) | MIT | Libre |  |
| 270 | `zod` | [colinhacks/zod](https://github.com/colinhacks/zod/tree/fef16cba0cf6668eb25ecc32fdfe2ce0a46f6f80) | MIT | Libre |  |
| 271 | `vitest` | [vitest-dev/vitest](https://github.com/vitest-dev/vitest/tree/cab34bb0ee23f00676ea895560c8b16399ce40b7) | MIT | Libre |  |
| 272 | `postal` | [postalserver/postal](https://github.com/postalserver/postal/tree/d96eddbadeda600595d6247486f9ceb8e99cbc15) | MIT | Libre |  |
| 273 | `instantsearch` | [algolia/instantsearch](https://github.com/algolia/instantsearch/tree/1066fcd5031876c4dab66b02e8f8216946040d12) | MIT | Libre |  |
| 274 | `maplibre` | [maplibre/maplibre-gl-js](https://github.com/maplibre/maplibre-gl-js/tree/04359f204e3e73ff0de36a30bba840a7091c5193) | MIT | Libre |  |
| 275 | `crowdsec` | [crowdsecurity/crowdsec](https://github.com/crowdsecurity/crowdsec/tree/e20782bb3c532f0b9b9a469c0bdaa003588ec8e5) | MIT | Libre |  |
| 276 | `vite-pwa` | [vite-pwa/vite-plugin-pwa](https://github.com/vite-pwa/vite-plugin-pwa/tree/355cf3dd283ca50da3ac4759501e9c3312a3da91) | MIT | Libre |  |
| 277 | `driverjs` | [kamranahmedse/driver.js](https://github.com/kamranahmedse/driver.js/tree/47e3c8761720c119aa08c3feb29b36e5b944938a) | MIT | Libre |  |
| 278 | `socketio` | [socketio/socket.io](https://github.com/socketio/socket.io/tree/f97d51a810d4f266122eb99bb6c083cd383638f0) | MIT | Libre |  |
| 279 | `mercadopago` | [mercadopago/sdk-nodejs](https://github.com/mercadopago/sdk-nodejs/tree/cdfecc30344d6e567c6b1b3b77d766339882b863) | MIT | Libre |  |
| 280 | `pdfme` | [pdfme/pdfme](https://github.com/pdfme/pdfme/tree/60d73ae0a0b707c241c14e3c70bcec9670c56113) | MIT | Libre |  |

## Bloque 6 — Motor de datos propios (la joya de la corona) (42)

| # | ID | Repositorio | Licencia | Política | Nota |
|---|---|---|---|---|---|
| 281 | `splink` | [moj-analytical-services/splink](https://github.com/moj-analytical-services/splink/tree/f319070e56c5b3666ec512811ac1820070f6f2e5) | MIT | Libre |  |
| 282 | `iceberg` | [apache/iceberg](https://github.com/apache/iceberg/tree/234d55774d3c7355f92c8e93f8e117b70726e556) | Apache-2.0 | Libre |  |
| 283 | `arrow` | [apache/arrow](https://github.com/apache/arrow/tree/ab5b42237dfe14d683bc74ecbddf71109a0c6633) | Apache-2.0 | Libre | LICENSE.txt incluye avisos MIT de terceros. |
| 284 | `polars` | [pola-rs/polars](https://github.com/pola-rs/polars/tree/5c36cdd75a30a8ab12a9f70e251c0f267235b2a7) | MIT | Libre |  |
| 285 | `ibis` | [ibis-project/ibis](https://github.com/ibis-project/ibis/tree/6d40f963fee940063e09956c7e60d073f4302259) | Apache-2.0 | Libre |  |
| 286 | `feast` | [feast-dev/feast](https://github.com/feast-dev/feast/tree/108c96704daa72015d8f447a5d503de964c45b3f) | Apache-2.0 | Libre |  |
| 287 | `openlineage` | [OpenLineage/OpenLineage](https://github.com/OpenLineage/OpenLineage/tree/c41626e99af0a02ad95a2805979167ad948ecb7b) | Apache-2.0 | Libre |  |
| 288 | `datahub` | [datahub-project/datahub](https://github.com/datahub-project/datahub/tree/164ce58a867afb6ee6ceac64c1c7aa9b526c1841) | Apache-2.0 | Libre |  |
| 289 | `apache-age` | [apache/age](https://github.com/apache/age/tree/8c7e44fd2a525dedfd3d4e8168921442eb4fce2f) | Apache-2.0 | Libre |  |
| 290 | `label-studio` | [HumanSignal/label-studio](https://github.com/HumanSignal/label-studio/tree/8831d8b9eb507ebb3ce29ab0021e494bc1893a16) | Apache-2.0 | Libre |  |
| 291 | `causalml` | [uber/causalml](https://github.com/uber/causalml/tree/d59bb520fc78410c01c443bad0ac57ea972844b8) | Apache-2.0 | Libre |  |
| 292 | `causal-learn` | [py-why/causal-learn](https://github.com/py-why/causal-learn/tree/0dacacf36390e3084704636bc3c36e82e35ee0cc) | MIT | Libre |  |
| 293 | `tfcausalimpact` | [WillianFuks/tfcausalimpact](https://github.com/WillianFuks/tfcausalimpact/tree/99bd5fb866acb352daf1b58c17d8f711d0e1a9ec) | Apache-2.0 | Libre |  |
| 294 | `pandera` | [unionai-oss/pandera](https://github.com/unionai-oss/pandera/tree/0292915e3321e83ee19380d7329788b7ead05291) | MIT | Libre |  |
| 295 | `ydata-profiling` | [ydataai/ydata-profiling](https://github.com/ydataai/ydata-profiling/tree/7f43aac68b2539bfe8f487f315aeaf44e965d29a) | MIT | Libre |  |
| 296 | `opendp` | [opendp/opendp](https://github.com/opendp/opendp/tree/11887ec1aa392f9f1cc08a37cf938962babac7a1) | MIT | Libre |  |
| 297 | `flaml` | [microsoft/FLAML](https://github.com/microsoft/FLAML/tree/46bce0ce989aae0271e68e5daac5b8a9b0522b87) | MIT | Libre |  |
| 298 | `chronos` | [amazon-science/chronos-forecasting](https://github.com/amazon-science/chronos-forecasting/tree/1224fafa91e1ecd6674f5204066b159e40b5e4a1) | Apache-2.0 | Libre |  |
| 299 | `recommenders` | [recommenders-team/recommenders](https://github.com/recommenders-team/recommenders/tree/cc47866b0599721f8544d1cc850a5a1db091acb3) | MIT | Libre |  |
| 300 | `shap` | [shap/shap](https://github.com/shap/shap/tree/511710def94e163a4678a1be07a74b9ccf0a4124) | MIT | Libre |  |
| 301 | `dvc` | [iterative/dvc](https://github.com/iterative/dvc/tree/b59add99ee667f2b352cc1be337619f965fe3fea) | Apache-2.0 | Libre |  |
| 302 | `sentence-transformers` | [UKPLab/sentence-transformers](https://github.com/UKPLab/sentence-transformers/tree/688fd663e7b242f41f3f62296d08c69937efeb00) | Apache-2.0 | Libre |  |
| 303 | `transformers` | [huggingface/transformers](https://github.com/huggingface/transformers/tree/0d7a6219179b24586089ae81b45cf725078e681f) | Apache-2.0 | Libre |  |
| 304 | `gliner` | [urchade/GLiNER](https://github.com/urchade/GLiNER/tree/beb41b3839267952d0f063c04dd6236e9fd93a38) | Apache-2.0 | Libre |  |
| 305 | `cube` | [cube-js/cube](https://github.com/cube-js/cube/tree/e19cbba0fcc1441c20eeef484408f340550c0225) | Apache-2.0 AND MIT | Libre | Apache-2.0 por defecto; algunos paquetes MIT. |
| 306 | `jitsu` | [jitsucom/jitsu](https://github.com/jitsucom/jitsu/tree/6c0d189a55c9e6c7b47d024d046e091ff1636565) | MIT | Libre |  |
| 307 | `arx` | [arx-deidentifier/arx](https://github.com/arx-deidentifier/arx/tree/4e0a5f5340fe9a58c44b34c2f9acd2d68f1dad5f) | Apache-2.0 | Libre |  |
| 308 | `fides` | [ethyca/fides](https://github.com/ethyca/fides/tree/e87f3ff835af368defc1ec42dc29ec545a288585) | Apache-2.0 | Libre |  |
| 309 | `river` | [online-ml/river](https://github.com/online-ml/river/tree/115df63c9cd57f904dd3a6d586b6cf32d2c1b2c8) | BSD-3-Clause | Libre |  |
| 310 | `vowpal` | [VowpalWabbit/vowpal_wabbit](https://github.com/VowpalWabbit/vowpal_wabbit/tree/00196b35f63bcb8a6d66966e2b4cf67d6a2bd335) | BSD-3-Clause | Libre |  |
| 311 | `ax` | [facebook/Ax](https://github.com/facebook/Ax/tree/fd8a67a524b063b2615815c638af2c94b034f476) | MIT | Libre |  |
| 312 | `faker` | [joke2k/faker](https://github.com/joke2k/faker/tree/affa2c5aada23fc5c00127298a8e904375d32832) | MIT | Libre |  |
| 313 | `sqlglot` | [tobymao/sqlglot](https://github.com/tobymao/sqlglot/tree/b476d29f42eeabfd0c8a150b9239a344b02e68dd) | MIT | Libre |  |
| 314 | `great-tables` | [posit-dev/great-tables](https://github.com/posit-dev/great-tables/tree/193bfc23b03a034aa5da8a1e7b471840ac2f3f8e) | MIT | Libre |  |
| 315 | `debezium` | [debezium/debezium](https://github.com/debezium/debezium/tree/a4c282ea70d3f913df699464f3e42f9ddb7eb03e) | Apache-2.0 | Libre |  |
| 316 | `cognee` | [topoteretes/cognee](https://github.com/topoteretes/cognee/tree/4053f6cc5536757f26a3665eed95c50088e6dc0b) | Apache-2.0 | Libre |  |
| 317 | `evidence` | [evidence-dev/evidence](https://github.com/evidence-dev/evidence/tree/4053bfba009e376ec51367ca7c2ca429dedce3c7) | MIT | Libre |  |
| 318 | `pyod` | [yzhao062/pyod](https://github.com/yzhao062/pyod/tree/9680a8b9d767d8226f76e5b3157ed318af881d74) | BSD-2-Clause | Libre |  |
| 319 | `mapie` | [scikit-learn-contrib/MAPIE](https://github.com/scikit-learn-contrib/MAPIE/tree/d5ea5e07aea09a897726fd8641c193850a5c540d) | BSD-3-Clause | Libre |  |
| 320 | `lifelines` | [CamDavidsonPilon/lifelines](https://github.com/CamDavidsonPilon/lifelines/tree/7a8fc34a013ecd79fa405017b89e1697c1cc6e17) | MIT | Libre |  |
| 321 | `datasketch` | [ekzhu/datasketch](https://github.com/ekzhu/datasketch/tree/c7eaaeea3f39909f906a9cf8ad4d21a878cb4e07) | MIT | Libre |  |
| 322 | `h3` | [uber/h3](https://github.com/uber/h3/tree/15920096d4a165729c01f749e2bd97334b009519) | Apache-2.0 | Libre |  |

