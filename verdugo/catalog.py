"""The requested 100 projects. Registration is NOT an implemented integration."""
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

GROUPS = [(10, 'commercial'), (22, 'content'), (32, 'research'),
          (38, 'orchestration'), (41, 'voice'), (51, 'data'),
          (60, 'analytics'), (70, 'modeling'), (80, 'ai'),
          (90, 'product'), (100, 'operations')]


def catalog():
    return [dict(number=i, id=slug, repository=repo,
                 source='https://github.com/' + repo,
                 domain=next(g for end, g in GROUPS if i <= end),
                 license_review='pending', artifact_pin=None,
                 live_verified=False)
            for i, (slug, repo) in enumerate(
                (line.split('|') for line in PROJECTS.splitlines()), 1)]


def graph(implemented=()):
    """Logical routing graph, never an assertion of running infrastructure."""
    nodes = catalog()
    return dict(nodes=[{'id': 'verdugo', 'domain': 'control'}] + nodes,
                edges=[{'from': 'verdugo', 'to': n['id'],
                        'kind': 'adapter' if n['id'] in implemented else 'planned',
                        'live': False} for n in nodes],
                domains=dict(Counter(n['domain'] for n in nodes)))
