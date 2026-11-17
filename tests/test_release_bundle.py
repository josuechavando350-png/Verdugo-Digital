"""Extracted distribution integrity, independent of Git and Node."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from verdugo import __version__
from verdugo.common import VerdugoError
from verdugo.release import verify

class ReleaseBundle(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        files={'panel/dist/index.html':'demo','verdugo/__main__.py':'# demo','sources/panel.json':'{}'}
        for name,content in files.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
        self.manifest={'schema':1,'version':__version__,'source_commit':'a'*40,
            'sha256':{name:hashlib.sha256(content.encode()).hexdigest() for name,content in files.items()}}
        self.save()
    def save(self): (self.root/'RELEASE.json').write_text(json.dumps(self.manifest))
    def test_verifies_compiled_panel_without_git_or_node_and_does_not_claim_signature(self):
        report=verify(self.root)
        self.assertEqual(report['files'],3);self.assertFalse(report['signature_verified'])
        (self.root/'verdugo/__pycache__').mkdir();(self.root/'verdugo/__pycache__/demo.pyc').touch()
        self.assertEqual(verify(self.root)['source_commit'],'a'*40)
    def test_modified_missing_and_unlisted_files_rejected(self):
        p=self.root/'panel/dist/index.html';p.write_text('changed')
        with self.assertRaises(VerdugoError):verify(self.root)
        p.unlink()
        with self.assertRaises(VerdugoError):verify(self.root)
        p.write_text('demo');(self.root/'panel/dist/injected.js').write_text('demo')
        with self.assertRaises(VerdugoError):verify(self.root)
    def test_paths_outside_release_and_symlink_components_rejected(self):
        for name in ('../outside','/outside','panel\\outside'):
            self.manifest['sha256'][name]='a'*64;self.save()
            with self.assertRaises(VerdugoError):verify(self.root)
            del self.manifest['sha256'][name]
        self.save();p=self.root/'panel/dist/index.html';p.unlink();p.symlink_to(self.root/'sources/panel.json')
        with self.assertRaises(VerdugoError):verify(self.root)
    def test_wrong_version_and_malformed_manifest_rejected(self):
        self.manifest['version']='0.0.0';self.save()
        with self.assertRaises(VerdugoError):verify(self.root)
        (self.root/'RELEASE.json').write_text('[]')
        with self.assertRaises(VerdugoError):verify(self.root)
