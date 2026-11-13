"""Native PostHog ClickHouse topology guards: these DO NOT certify service startup."""
from pathlib import Path
import importlib.util
import xml.etree.ElementTree as ET
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY = ROOT / "deploy/native/posthog-clickhouse-single.xml"

class PostHogTopologyGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(TOPOLOGY).getroot()

    def test_all_original_posthog_cluster_contracts_present(self):
        upstream = {"posthog","posthog_single_shard","posthog_migrations",
                    "posthog_writable","posthog_primary_replica",
                    "ai_events","aux","ops","sessions"}
        servers = self.root.find("remote_servers")
        self.assertEqual({c.tag for c in servers},upstream)
        for cluster in servers:
            shards = cluster.findall("shard")
            self.assertEqual(len(shards),1)
            replicas = shards[0].findall("replica")
            self.assertEqual(len(replicas),1)
            self.assertEqual(replicas[0].findtext("host"),"ph-clickhouse")
            self.assertEqual(replicas[0].findtext("port"),"9000")

    def test_kafka_collections_and_zookeeper_are_internal(self):
        collections = self.root.find("named_collections")
        self.assertGreaterEqual(len(collections),8)
        for collection in collections:
            self.assertEqual(collection.find("kafka_broker_list").attrib,{"from_env":"KAFKA_HOSTS"})
        self.assertEqual(self.root.findtext("zookeeper/node/host"),"ph-zookeeper")
        self.assertEqual(self.root.findtext("zookeeper/node/port"),"2181")
        self.assertEqual(self.root.findtext("macros/hostClusterRole"),"data")

    def test_no_remote_hosts_or_auth_bypass_in_topology(self):
        raw=TOPOLOGY.read_text()
        self.assertNotIn("http://",raw)
        self.assertNotIn("https://",raw)
        self.assertNotIn("<users>",raw)
        self.assertNotIn("<password>",raw)
        self.assertNotIn("<skip_check_for_incorrect_settings>",raw)

    def test_original_upstream_migrations_still_invoked(self):
        native = (ROOT/"scripts/native_posthog.py").read_text()
        self.assertIn("python manage.py migrate --noinput",native)
        self.assertIn("python manage.py migrate_clickhouse",native)
        self.assertIn("posthog.wsgi:application",native)
        self.assertIn("posthog_clickhouse_native_cluster_contract_missing",native)
        self.assertIn("ph-zookeeper",native)
        self.assertIn("posthog-native.xml",native)
        self.assertIn("event_capture_verified':False",native)

if __name__ == "__main__":
    unittest.main()
