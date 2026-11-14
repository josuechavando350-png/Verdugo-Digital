"""Unified Verdugo catalogue: the original 100 plus the v0.14 expansion (322 entries).

Registration is NOT an implemented integration. 22 entries of the original 100
remain registered only as excluded by license policy (see license_policy.py);
the other 300 are the permissive-license portfolio.
"""
from collections import Counter

# Stable IDs; source: Nexus_100_repos_evidencias.json (user-approved shortlist).
PROJECTS = '''twenty|twentyhq/twenty
frappe-crm|frappe/crm
erpnext|frappe/erpnext
odoo|odoo/odoo
mautic|mautic/mautic
chatwoot|chatwoot/chatwoot
listmonk|knadh/listmonk
dittofeed|dittofeed/dittofeed
novu|novuhq/novu
easyappointments|alextselegidis/easyappointments
astro|withastro/astro
payload|payloadcms/payload
ghost|TryGhost/Ghost
grapesjs|GrapesJS/grapesjs
formbricks|formbricks/formbricks
documenso|documenso/documenso
postiz|gitroomhq/postiz-app
dub|dubinc/dub.link
shlink|shlinkio/shlink
react-email|resend/react-email
comfyui|Comfy-Org/ComfyUI
remotion|remotion-dev/remotion
scrapy|scrapy/scrapy
crawlee|apify/crawlee
playwright|microsoft/playwright
changedetection|dgtlmoon/changedetection.io
trafilatura|adbar/trafilatura
crawl4ai|unclecode/crawl4ai
lighthouse|GoogleChrome/lighthouse
lighthouse-ci|GoogleChrome/lighthouse-ci
google-ads|googleads/google-ads-python
meta-ads|meta/facebook-python-business-sdk
activepieces|activepieces/activepieces
n8n|n8n-io/n8n
temporal|temporalio/temporal
trigger|triggerdotdev/trigger.dev
nango|NangoHQ/nango
dagster|dagster-io/dagster
livekit|livekit/agents
pipecat|pipecat-ai/pipecat
whisper|openai/whisper
dlt|dlt-hub/dlt
airbyte|airbytehq/airbyte
dbt|dbt-labs/dbt
duckdb|duckdb/duckdb
clickhouse|ClickHouse/ClickHouse
postgres|postgres/postgres
pgvector|pgvector/pgvector
qdrant|qdrant/qdrant
meilisearch|meilisearch/meilisearch
docling|docling-project/docling
posthog|PostHog/posthog
umami|umami-software/umami
plausible|plausible/analytics
matomo|matomo-org/matomo
metabase|metabase/metabase
superset|apache/superset
growthbook|growthbook/growthbook
robyn|facebookexperimental/Robyn
meridian|google/meridian
econml|py-why/EconML
dowhy|py-why/dowhy
pymc-marketing|pymc-labs/pymc-marketing
or-tools|google/or-tools
optuna|optuna/optuna
scikit-learn|scikit-learn/scikit-learn
catboost|catboost/catboost
mlflow|mlflow/mlflow
evidently|evidentlyai/evidently
great-expectations|fivetran/great_expectations
langgraph|langchain-ai/langgraph
pydantic-ai|pydantic/pydantic-ai
llama-index|run-llama/llama_index
haystack|deepset-ai/haystack
langfuse|langfuse/langfuse
promptfoo|promptfoo/promptfoo
ragas|vibrantlabsai/ragas
dspy|stanfordnlp/dspy
bifrost|maximhq/bifrost
presidio|data-privacy-stack/presidio
medusa|medusajs/medusa
saleor|saleor/saleor
lago|getlago/lago
killbill|killbill/killbill
openmeter|openmeterio/openmeter
better-auth|better-auth/better-auth
keycloak|keycloak/keycloak
openfga|openfga/openfga
unleash|Unleash/unleash
supabase|supabase/supabase
coolify|coollabsio/coolify
grafana|grafana/grafana
prometheus|prometheus/prometheus
otel-collector|open-telemetry/opentelemetry-collector
sops|getsops/sops
infisical|Infisical/infisical
grype|anchore/grype
syft|anchore/syft
gitleaks|gitleaks/gitleaks
restic|restic/restic'''

# v0.14 expansion: id|repository|domain. Observed and pinned on 2026-11-13.
PROJECTS_V014 = '''openprospector|clawnify/OpenProspector|marketing
langflow|langflow-ai/langflow|marketing
openrefine|OpenRefine/OpenRefine|marketing
openseo|duckduckdeploy/openseo|marketing
mcp-gsc|AminForou/mcp-gsc|marketing
siteone-crawler|janreges/siteone-crawler|marketing
advertools|eliasdabbas/advertools|marketing
cal-diy|calcom/cal.diy|marketing
uptime-kuma|louislam/uptime-kuma|marketing
opengmb|synectus/OpenGMB|marketing
kingfisher-collect|open-contracting/kingfisher-collect|marketing
markitdown|microsoft/markitdown|marketing
spacy|explosion/spaCy|marketing
schema-dts|google/schema-dts|marketing
web-vitals|GoogleChrome/web-vitals|marketing
altcha|altcha-org/altcha|marketing
cookieconsent|orestbida/cookieconsent|marketing
libphonenumber|google/libphonenumber|marketing
twilio-python|twilio/twilio-python|marketing
stripe-python|stripe/stripe-python|marketing
parsedmarc|domainaware/parsedmarc|marketing
geo-optimizer|Auriti-Labs/geo-optimizer-skill|authority
geo-lint|IJONIS/geo-lint|authority
autogeo|cxcscmu/AutoGEO|authority
site-md|yazinsai/site-md|authority
nlweb|microsoft/NLWeb|authority
goaccess|allinurl/goaccess|authority
ipranges|lord-alfred/ipranges|authority
anubis|TecharoHQ/anubis|authority
the-great-gpt-firewall|samber/the-great-gpt-firewall|authority
seo-graph|jdevalk/seo-graph|authority
structured-data-validator|adobe/structured-data-validator|authority
pywikibot|wikimedia/pywikibot|authority
id-openstreetmap|openstreetmap/iD|authority
sherlock|sherlock-project/sherlock|authority
indexnow-for-python|jakob-bagterp/index-now-for-python|authority
feed|jpmonette/feed|authority
cdx-toolkit|cocrawler/cdx_toolkit|authority
cc-webgraph|commoncrawl/cc-webgraph|authority
trendspyg|flack0x/trendspyg|authority
waybackpy|akamhy/waybackpy|authority
newsjack|elvisun/newsjack|authority
gdeltdoc|alex9smith/gdelt-doc-api|authority
news-please|fhamborg/news-please|authority
python-podcastindex|piqosoft/python-podcastindex|authority
praw|praw-dev/praw|authority
youtube-comment-downloader|egbertbouman/youtube-comment-downloader|authority
people-also-ask|labsonmars/people_also_ask|authority
google-maps-scraper|gosom/google-maps-scraper|authority
dnstwist|elceef/dnstwist|authority
c2pa|contentauth/c2pa-rs|authority
vale|errata-ai/vale|authority
datasette|simonw/datasette|authority
ckanapi|ckan/ckanapi|authority
quarto|quarto-dev/quarto-cli|authority
owncast|owncast/owncast|authority
auto-editor|WyattBlue/auto-editor|authority
slidev|slidevjs/slidev|authority
carousel-generator|FranciscoMoretti/carousel-generator|authority
excalidraw|excalidraw/excalidraw|authority
apache-answer|apache/answer|authority
local-seo-skills|garrettjsmith/localseoskills|authority
a2a|a2aproject/A2A|authority
webmention-io|aaronpk/webmention.io|authority
claude-skills-c-level|alirezarezvani/claude-skills|strategy
tinytroupe|microsoft/TinyTroupe|strategy
gpt-researcher|assafelovic/gpt-researcher|strategy
forecasting-tools|Metaculus/forecasting-tools|strategy
onlinewardleymaps|damonsk/onlinewardleymaps|strategy
operately|operately/operately|strategy
bpmn-js|bpmn-io/bpmn-js|strategy
landscape-app|cncf/landscapeapp|strategy
datosmex|andreslomeliv/DatosMex|strategy
wbgapi|tgherzog/wbgapi|strategy
census|datamade/census|strategy
comtradeapicall|uncomtrade/comtradeapicall|strategy
py-ecomplexity|cid-harvard/py-ecomplexity|strategy
openbb|OpenBB-finance/OpenBB|strategy
financetoolkit|JerBouma/FinanceToolkit|strategy
jobspy|speedyapply/JobSpy|strategy
osmnx|gboeing/osmnx|strategy
kepler-gl|keplergl/kepler.gl|strategy
taguette|remram44/taguette|strategy
bertopic|MaartenGr/BERTopic|strategy
pricesensitivitymeter|max-alletsee/pricesensitivitymeter|strategy
squiggle|quantified-uncertainty/squiggle|strategy
statsforecast|Nixtla/statsforecast|strategy
statsmodels|statsmodels/statsmodels|strategy
mlxtend|rasbt/mlxtend|strategy
networkx|networkx/networkx|strategy
pymcdm|kotbaton/pymcdm|strategy
nashpy|drvinceknight/Nashpy|strategy
mesa|projectmesa/mesa|strategy
pysd|SDXorg/pysd|strategy
numpy-financial|numpy/numpy-financial|strategy
graphrag|microsoft/graphrag|strategy
vanna|vanna-ai/vanna|strategy
marimo|marimo-team/marimo|strategy
grist|gristlabs/grist-core|strategy
log4brains|thomvaill/log4brains|strategy
crewai|crewAIInc/crewAI|agents
openai-agents|openai/openai-agents-python|agents
google-adk|google/adk-python|agents
agent-framework|microsoft/agent-framework|agents
smolagents|huggingface/smolagents|agents
camel|camel-ai/camel|agents
mastra|mastra-ai/mastra|agents
any-agent|mozilla-ai/any-agent|agents
langchain|langchain-ai/langchain|agents
langgraph-supervisor|langchain-ai/langgraph-supervisor-py|agents
letta|letta-ai/letta|agents
mem0|mem0ai/mem0|agents
graphiti|getzep/graphiti|agents
browser-use|browser-use/browser-use|agents
stagehand|browserbase/stagehand|agents
playwright-mcp|microsoft/playwright-mcp|agents
mcp-python-sdk|modelcontextprotocol/python-sdk|agents
mcp-typescript-sdk|modelcontextprotocol/typescript-sdk|agents
fastmcp|PrefectHQ/fastmcp|agents
mcp-agent|lastmile-ai/mcp-agent|agents
e2b|e2b-dev/E2B|agents
guardrails|guardrails-ai/guardrails|agents
nemo-guardrails|NVIDIA/NeMo-Guardrails|agents
instructor|567-labs/instructor|agents
outlines|dottxt-ai/outlines|agents
ollama|ollama/ollama|agents
vllm|vllm-project/vllm|agents
openhands|All-Hands-AI/OpenHands|agents
storm|stanford-oval/storm|agents
magentic-ui|microsoft/magentic-ui|agents
humanlayer|humanlayer/humanlayer|agents
cua|trycua/cua|agents
composio|ComposioHQ/composio|agents
ag-ui|ag-ui-protocol/ag-ui|agents
copilotkit|CopilotKit/CopilotKit|agents
vercel-ai-sdk|vercel/ai|agents
assistant-ui|assistant-ui/assistant-ui|agents
steel-browser|steel-dev/steel-browser|agents
llm-guard|protectai/llm-guard|agents
a2a-python|a2aproject/a2a-python|agents
trpc|trpc/trpc|platform
hono|honojs/hono|platform
fastapi|fastapi/fastapi|platform
drizzle|drizzle-team/drizzle-orm|platform
nextjs|vercel/next.js|platform
shadcn-ui|shadcn-ui/ui|platform
tailwindcss|tailwindlabs/tailwindcss|platform
refine|refinedev/refine|platform
echarts|apache/echarts|platform
tanstack-query|TanStack/query|platform
tanstack-table|TanStack/table|platform
i18next|i18next/i18next|platform
seaweedfs|seaweedfs/seaweedfs|platform
caddy|caddyserver/caddy|platform
openapi-generator|OpenAPITools/openapi-generator|platform
scalar|scalar/scalar|platform
starlight|withastro/starlight|platform
svix|svix/svix-webhooks|platform
bullmq|taskforcesh/bullmq|platform
valkey|valkey-io/valkey|platform
tusd|tus/tusd|platform
uppy|transloadit/uppy|platform
sharp|lovell/sharp|platform
surveyjs|surveyjs/survey-library|platform
tiptap|ueberdosis/tiptap|platform
gotenberg|gotenberg/gotenberg|platform
signoz|SigNoz/signoz|platform
expo|expo/expo|platform
hoppscotch|hoppscotch/hoppscotch|platform
zod|colinhacks/zod|platform
vitest|vitest-dev/vitest|platform
postal|postalserver/postal|platform
instantsearch|algolia/instantsearch|platform
maplibre|maplibre/maplibre-gl-js|platform
crowdsec|crowdsecurity/crowdsec|platform
vite-pwa|vite-pwa/vite-plugin-pwa|platform
driverjs|kamranahmedse/driver.js|platform
socketio|socketio/socket.io|platform
mercadopago|mercadopago/sdk-nodejs|platform
pdfme|pdfme/pdfme|platform
splink|moj-analytical-services/splink|dataengine
iceberg|apache/iceberg|dataengine
arrow|apache/arrow|dataengine
polars|pola-rs/polars|dataengine
ibis|ibis-project/ibis|dataengine
feast|feast-dev/feast|dataengine
openlineage|OpenLineage/OpenLineage|dataengine
datahub|datahub-project/datahub|dataengine
apache-age|apache/age|dataengine
label-studio|HumanSignal/label-studio|dataengine
causalml|uber/causalml|dataengine
causal-learn|py-why/causal-learn|dataengine
tfcausalimpact|WillianFuks/tfcausalimpact|dataengine
pandera|unionai-oss/pandera|dataengine
ydata-profiling|ydataai/ydata-profiling|dataengine
opendp|opendp/opendp|dataengine
flaml|microsoft/FLAML|dataengine
chronos|amazon-science/chronos-forecasting|dataengine
recommenders|recommenders-team/recommenders|dataengine
shap|shap/shap|dataengine
dvc|iterative/dvc|dataengine
sentence-transformers|UKPLab/sentence-transformers|dataengine
transformers|huggingface/transformers|dataengine
gliner|urchade/GLiNER|dataengine
cube|cube-js/cube|dataengine
jitsu|jitsucom/jitsu|dataengine
arx|arx-deidentifier/arx|dataengine
fides|ethyca/fides|dataengine
river|online-ml/river|dataengine
vowpal|VowpalWabbit/vowpal_wabbit|dataengine
ax|facebook/Ax|dataengine
faker|joke2k/faker|dataengine
sqlglot|tobymao/sqlglot|dataengine
great-tables|posit-dev/great-tables|dataengine
debezium|debezium/debezium|dataengine
cognee|topoteretes/cognee|dataengine
evidence|evidence-dev/evidence|dataengine
pyod|yzhao062/pyod|dataengine
mapie|scikit-learn-contrib/MAPIE|dataengine
lifelines|CamDavidsonPilon/lifelines|dataengine
datasketch|ekzhu/datasketch|dataengine
h3|uber/h3|dataengine'''

GROUPS = [(10, 'commercial'), (22, 'content'), (32, 'research'),
          (38, 'orchestration'), (41, 'voice'), (51, 'data'),
          (60, 'analytics'), (70, 'modeling'), (80, 'ai'),
          (90, 'product'), (100, 'operations')]


CORE_COUNT = 100


def catalog():
    rows = [dict(number=i, id=slug, repository=repo,
                 source='https://github.com/' + repo,
                 domain=next(g for end, g in GROUPS if i <= end),
                 license_review='pending', artifact_pin=None,
                 live_verified=False)
            for i, (slug, repo) in enumerate(
                (line.split('|') for line in PROJECTS.splitlines()), 1)]
    for i, line in enumerate(PROJECTS_V014.splitlines(), CORE_COUNT + 1):
        slug, repo, domain = line.split('|')
        rows.append(dict(number=i, id=slug, repository=repo,
                         source='https://github.com/' + repo, domain=domain,
                         license_review='pending', artifact_pin=None,
                         live_verified=False))
    return rows


def graph(implemented=()):
    """Logical routing graph, never an assertion of running infrastructure."""
    nodes = catalog()
    return dict(nodes=[{'id': 'verdugo', 'domain': 'control'}] + nodes,
                edges=[{'from': 'verdugo', 'to': n['id'],
                        'kind': 'adapter' if n['id'] in implemented else 'planned',
                        'live': False} for n in nodes],
                domains=dict(Counter(n['domain'] for n in nodes)))
