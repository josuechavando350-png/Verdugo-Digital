import json
from pathlib import Path
import shutil
import tempfile
import unittest
from verdugo import connections,panel_components
from verdugo.common import VerdugoError
ROOT=Path(__file__).resolve().parents[1]

class PanelEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        rows=json.loads((ROOT/'sources/panel.json').read_text())['components']
        paths={'sources/panel.json','sources/connections.json','panel/package.json','panel/package-lock.json','panel/requirements.txt','panel/constraints.txt'}
        paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'sources/parts').glob('*.json'))
        for r in rows:
            if r['integrated']:paths.update([r['usage']['file'],r['test']['file']])
        for path in paths:
            dest=self.root/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,dest)
    def modify(self,path,change):
        p=self.root/path;p.write_text(change(p.read_text()))
    def invalid(self):
        with self.assertRaises(VerdugoError):panel_components.validate(self.root)
    def test_56_decisions_and_13_integrations_are_computed(self):
        self.assertEqual(len(panel_components.validate(self.root)),13)
        self.assertEqual(connections.summary()['states'],{'conectado':244,'integrado_en_panel':13,'pieza_de_construccion':43,'pendiente':0,'excluido':22})
        self.assertEqual(connections.state('astro'),'integrado_en_panel');self.assertEqual(connections.state('nextjs'),'pieza_de_construccion')
    def test_package_version_mismatch_fails(self):
        self.modify('panel/package.json',lambda s:s.replace('7.4.11','7.4.12'));self.invalid()
    def test_lock_version_mismatch_fails(self):
        def changed(s):
            d=json.loads(s);d['packages']['node_modules/astro']['version']='0.0.0';return json.dumps(d)
        self.modify('panel/package-lock.json',changed);self.invalid()
    def test_empty_import_does_not_count_without_invocation(self):
        self.modify('panel/src/components/DataTable.tsx',lambda s:s.replace('useTable(','unused('));self.invalid()
    def test_missing_test_fails(self):
        (self.root/'panel/tests/panel.test.tsx').unlink();self.invalid()
    def test_wrong_source_commit_fails(self):
        def changed(s):
            d=json.loads(s);next(r for r in d['components'] if r['id']=='astro')['source']['commit_sha']='0'*40;return json.dumps(d)
        self.modify('sources/panel.json',changed);self.invalid()
    def test_missing_component_decision_fails(self):
        def changed(s):
            d=json.loads(s);d['components'].pop();return json.dumps(d)
        self.modify('sources/panel.json',changed);self.invalid()
    def test_python_dependency_lock_must_match(self):
        self.modify('panel/constraints.txt',lambda s:s.replace('fastapi==0.162.7','fastapi==0.0.0'));self.invalid()
