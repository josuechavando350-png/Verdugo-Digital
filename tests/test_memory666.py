"""Boundaries for the fixed original MCP memory-server operation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo.common import VerdugoError
from verdugo import local_memory666 as memory
from verdugo.registry666 import read_registry


class Memory666Tests(unittest.TestCase):
    def test_no_free_text_paths_credentials_tools_or_unknown_edges(self):
        p={'dataset':'demo','statuses':['completed','blocked'],'edges':[[0,1]],'query':'blocked'}
        memory.validate('servers','graph.audit',p)
        for change in ({'query':'private name'}, {'path':'/tmp/graph'}, {'tool':'read_graph'},
                       {'statuses':['arbitrary']}, {'edges':[[0,2]]}, {'edges':[[True,0]]},
                       {'edges':[[0,0]]}, {'edges':[[0,1]]*65}, {'dataset':'real'}):
            with self.subTest(change=change),self.assertRaises(VerdugoError):
                memory.validate('servers','graph.audit',p|change)

    def test_source_contract_and_sdk_have_separate_pins(self):
        r=json.loads(memory.CONTRACT.read_text())
        registered=next(x for x in read_registry()['records'] if x['id']=='servers')
        self.assertEqual(registered['commit_sha'],r['commit'])
        self.assertEqual(3,len(r['sdk_dependency']['verified_files']))
        self.assertEqual(6,len(r['files']))
        self.assertIn('upstream/src/memory/dist/index.js',r['artifacts'])
        self.assertEqual(64,len(r['node_binary_sha256']))

    def test_tampered_node_is_unavailable_before_the_mcp_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'bin').mkdir();(root/'bin/node').write_bytes(b'altered')
            (root/'bin/node').chmod(0o700)
            with patch.dict('os.environ',{memory.ENV:tmp}):
                self.assertFalse(memory.runtime_state('servers')['version_matches'])
