import base64
from contextlib import closing
from pathlib import Path
import os
import unittest
import zlib

from verdugo import local_runtime
from verdugo.__main__ import template
from verdugo.engine import Engine


class C2paNative(unittest.TestCase):
    def test_missing_tampered_and_remote_manifests_do_not_become_trusted(self):
        selected = os.getenv('VERDUGO_RUNTIME_SERVICES', '').split(',')
        if 'c2pa' not in selected:
            self.skipTest('Other runtime group selected')
        if not local_runtime.installed('c2pa')['version_matches']:
            if os.getenv('VERDUGO_RUNTIME_REQUIRED') == '1': self.fail('Missing C2PA runtime')
            self.skipTest('Missing optional runtime')
        config = template('nexus')
        config['tenants']['nexus']['services']['c2pa'].update(enabled=True, license_reviewed=True, runtime_reviewed=True)
        home = Path(__file__).parent/'fixtures/c2pa'
        signed = bytearray((home/'signed-test.png').read_bytes())
        signed[19] ^= 1  # Change IHDR width while retaining a valid PNG chunk CRC.
        signed[29:33] = zlib.crc32(signed[12:29]).to_bytes(4, 'big')
        with closing(Engine(':memory:', config)) as e:
            def run(key, raw):
                return e.execute({'service': 'c2pa', 'operation': 'manifest.inspect', 'key': key,
                                  'params': {'dataset': 'demo', 'secret_text': base64.b64encode(raw).decode()}}, True)
            unsigned = run('unsigned', (home/'unsigned-test.png').read_bytes())
            self.assertEqual('succeeded', unsigned['state'], unsigned)
            self.assertFalse(unsigned['result']['result']['embedded_manifest_found'])
            changed = run('tampered', signed)
            self.assertEqual('succeeded', changed['state'], changed)
            self.assertFalse(changed['result']['result']['authenticity_certified'])
            self.assertGreater(changed['result']['result']['active_manifest_diagnostics']['failure'], 1)
            remote = run('remote', (home/'remote-test.png').read_bytes())
            self.assertNotEqual('succeeded', remote['state'])
            self.assertNotIn('localhost:5000', str(remote))
