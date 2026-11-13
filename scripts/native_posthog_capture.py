"""Real PostHog analytics ingestion: Rust capture -> Redpanda -> original Node worker -> ClickHouse.

A capture HTTP acknowledgement is NEVER sufficient: data must be read back using
the authenticated original PostHog events API, then survive restarts.
This is an ephemeral CI laboratory, not a supported production PostHog installer.
"""
from __future__ import annotations

import json
import secrets
import time
import uuid
import urllib.parse

# Official component images identified in the upstream PostHog docker-compose base.
# Resolved to image IDs and observed digests by native-pair-acceptance.py on every run.
# They are not asserted equivalent to the pinned Git submodule commit.
IMAGES = {
    'posthog_kafka': 'docker.io/redpandadata/redpanda:v25.1.9',
    'posthog_capture': 'ghcr.io/posthog/posthog/capture:master',
    'posthog_ingestion': 'ghcr.io/posthog/posthog-node:master',
}


def normalize_event_result(value):
    """Only the original API event list can establish persistent event capture."""
    if not isinstance(value, dict):
        return []
    data = value.get('results')
    return data if isinstance(data, list) else []


def recorded_event(value, *, event_id, event_name, subject, route):
    matches = []
    for row in normalize_event_result(value):
        if not isinstance(row, dict):
            continue
        props = row.get('properties', {})
        if isinstance(props, str):
            try:
                props = json.loads(props)
            except (ValueError, TypeError):
                continue
        if not isinstance(props, dict):
            continue
        row_id = str(row.get('uuid') or row.get('id') or '')
        if (row_id.lower() == event_id.lower()
                and row.get('event') == event_name
                and str(row.get('distinct_id')) == subject
                and props.get('verdugo_route') == route
                and props.get('native_synthetic') is True):
            matches.append(row)
    return len(matches) == 1


class PostHogCapture:
    def __init__(self, app):
        self.app = app
        self.n = app.n
        self.base = None
        self.last_id = None
        self.last_name = None
        self.last_subject = None
        self.last_route = None

    def start_kafka(self):
        a = self.app
        args = (
            'redpanda','start',
            '--kafka-addr', 'internal://0.0.0.0:9092,external://0.0.0.0:19092',
            '--advertise-kafka-addr', 'internal://kafka:9092,external://localhost:19092',
            '--pandaproxy-addr', 'internal://0.0.0.0:8082',
            '--rpc-addr', 'kafka:33145',
            '--advertise-rpc-addr', 'kafka:33145',
            '--mode', 'dev-container', '--smp', '1', '--memory', '1G',
            '--reserve-memory', '0M', '--overprovisioned',
            '--set', 'redpanda.auto_create_topics_enabled=true',
        )
        a.launch('ph-kafka', 'posthog_kafka', alias='kafka', args=args)
        kafka=a.find('ph-kafka')
        a.wait(lambda: a.docker('exec',kafka,'rpk','cluster','health',timeout=10),seconds=180)

    def start_workers(self, *, database, redis, clickhouse_password, salt):
        a = self.app
        # CAPTURE_MODE, Kafka topic and consumer mode match the *original*
        # upstream Docker Compose services. Do not proxy events through a mock.
        capture_env = {
            'ADDRESS':'0.0.0.0:3000',
            'KAFKA_TOPIC':'events_plugin_ingestion',
            'CAPTURE_OUTPUT_ANALYTICS_MAIN_TOPIC':'events_plugin_ingestion',
            'KAFKA_HOSTS':'kafka:9092',
            'KAFKA_INGESTION_PRODUCER_METADATA_BROKER_LIST':'kafka:9092',
            'REDIS_URL':redis,
            'CAPTURE_MODE':'events',
            'RUST_LOG':'warn,rdkafka=error',
        }
        ingest_env = {
            'PLUGIN_SERVER_MODE':'ingestion-v2-combined',
            'DATABASE_URL':database,
            'PERSONS_DATABASE_URL':database,
            'BEHAVIORAL_COHORTS_DATABASE_URL':database,
            'KAFKA_HOSTS':'kafka:9092',
            'REDIS_URL':redis,
            'CLICKHOUSE_HOST':'ph-clickhouse',
            'CLICKHOUSE_DATABASE':'posthog',
            'CLICKHOUSE_USER':'default',
            'CLICKHOUSE_PASSWORD':clickhouse_password,
            'CLICKHOUSE_SECURE':'false',
            'CLICKHOUSE_VERIFY':'false',
            'COOKIELESS_REDIS_HOST':'ph-redis',
            'COOKIELESS_REDIS_PORT':'6379',
            'CDP_REDIS_HOST':'ph-redis',
            'ENCRYPTION_SALT_KEYS':salt,
            'NODE_OPTIONS':'--max-old-space-size=850',
        }
        self.base=a.launch('ph-capture','posthog_capture',port=3000,env=capture_env)
        a.launch('ph-ingestion','posthog_ingestion',env=ingest_env)
        a.wait(lambda:a.http.call(self.base+'/_liveness',raw=True) is not None,seconds=240)

    def capture_and_readback(self, identity, *, project_token, timeout=240):
        a=self.app
        if not self.base or not isinstance(project_token,str) or len(project_token)<10:
            raise self.n.AcceptanceError('posthog_original_capture_not_configured')
        if not isinstance(identity,dict) or any(key not in identity for key in ('event_id','event_name','subject','route')):
            raise self.n.AcceptanceError('posthog_missing_canonical_event')
        # Never include real email, name or user identifiers in this test.
        payload={
            'token':project_token,'uuid':identity['event_id'],
            'event':identity['event_name'],'distinct_id':identity['subject'],
            'properties':{
                'verdugo_route':identity['route'],
                'native_synthetic':True,
                '$process_person_profile':False,
            }
        }
        # The original Rust capture API responds before storage. Readback below
        # is mandatory and uses a *different*, authenticated Django API.
        a.http.call(self.base+'/i/v0/e/',data=payload,raw=True)
        self.last_id=identity['event_id']
        self.last_name=identity['event_name']
        self.last_subject=identity['subject']
        self.last_route=identity['route']
        a.wait(self.readback,seconds=timeout)
        return True

    def readback(self):
        a=self.app
        if not self.last_id:
            return False
        query=urllib.parse.urlencode({'event':self.last_name,'limit':100})
        result=a.http.call(a.base+'/api/projects/'+str(a.team)+'/events/?'+query,headers=a.headers)
        return recorded_event(
            result,event_id=self.last_id,event_name=self.last_name,
            subject=self.last_subject,route=self.last_route)

    def restart(self):
        a=self.app
        # Dependents are stopped before Kafka. No reset/reseed of stored events.
        a.docker('stop',a.find('ph-capture'),a.find('ph-ingestion'),timeout=90)
        a.docker('restart',a.find('ph-kafka'),timeout=90)
        kafka=a.find('ph-kafka')
        a.wait(lambda:a.docker('exec',kafka,'rpk','cluster','health',timeout=10),seconds=180)
        a.docker('start',a.find('ph-ingestion'))
        a.docker('start',a.find('ph-capture'))
        self.base=a.refresh('ph-capture',3000)
        a.wait(lambda:a.http.call(self.base+'/_liveness',raw=True) is not None,seconds=240)

    def verify_after_restart(self):
        a=self.app
        a.wait(self.readback,seconds=240)
        # New event after restart rules out a stale, read-only ingester.
        fresh={
            'event_id':str(uuid.uuid4()),
            'event_name':'verdugo_native_after_restart_'+secrets.token_hex(8),
            'subject':self.last_subject,'route':self.last_route,
        }
        self.capture_and_readback(fresh,project_token=a.project_token,timeout=240)
        a.proof['event_capture_verified']=True
        a.proof['event_capture_after_restart_verified']=True
        a.proof['scope']='original_rust_capture_kafka_cdp_clickhouse_readback'
        a.check('event_capture_readback')
        a.check('event_capture_after_restart')
