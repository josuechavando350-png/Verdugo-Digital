"""Boundaries and original source/build binding; real EBM executes in acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_explain666 as explain
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset':'demo', 'training':[
    {'contacts':10+i, 'spend_minor':50*i, 'observed_clients':i} for i in range(8)],
    'queries':[{'contacts':20,'spend_minor':100}]}


class Explain666Tests(unittest.TestCase):
    def test_rejects_models_code_paths_and_unbounded_training(self):
        explain.validate('interpret', 'prediction.explain', CASE)
        for changes in ({'dataset':'real'}, {'model':'/tmp/x'}, {'code':'1+1'},
                        {'callbacks':[]}, {'training':CASE['training'][:7]},
                        {'training':CASE['training']*5}, {'queries':[]},
                        {'queries':CASE['queries']*5}):
            with self.subTest(changes=changes), self.assertRaises(VerdugoError):
                explain.validate('interpret', 'prediction.explain', CASE | changes)

    def test_rows_reject_private_fields_coercion_and_impossible_counts(self):
        for key, value in [('contacts',True),('contacts',1001),('spend_minor',-1),
                           ('observed_clients',11),('email','private@example.invalid')]:
            p=copy.deepcopy(CASE);p['training'][0][key]=value
            with self.subTest(key=key), self.assertRaises(VerdugoError):
                explain.validate('interpret','prediction.explain',p)
        with self.assertRaises(VerdugoError):
            explain.validate('interpret','model.publish',CASE)

    def test_source_pin_covers_original_python_and_native_build(self):
        record=json.loads(explain.CONTRACT.read_text())
        source=next(r for r in read_registry()['records'] if r['id']=='interpret')
        self.assertEqual(source['commit_sha'],record['commit'])
        self.assertEqual(82,sum(bool(f['installed_path']) for f in record['files']))
        self.assertIn('build.sh',{f['path'] for f in record['files']})
        lock=explain.CONTRACT.parent.parent/'requirements/runtime-interpret666.lock.json'
        self.assertEqual(record['npm_lock_sha256'],hashlib.sha256(lock.read_bytes()).hexdigest())
        self.assertEqual(1,explain.SETTINGS['n_jobs'])
        self.assertEqual(16,explain.SETTINGS['max_rounds'])

    def test_native_mutation_or_alternate_loader_candidate_fails_closed(self):
        record=json.loads(explain.CONTRACT.read_text()) | {'files':[]}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);artifacts={}
            for name in explain.BUILD_FILES:
                path=root/explain.PACKAGE/name;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b'integrity fixture, never imported')
                artifacts[name]=hashlib.sha256(path.read_bytes()).hexdigest()
            receipt={'schema':'verdugo.interpret666.operator-build.v1',
                'commit':record['commit'],'archive_sha256':record['archive_sha256'],
                'build_arguments':['-release_64'],'npm_lock_sha256':record['npm_lock_sha256'],
                'artifacts':artifacts}
            path=root/explain.RECEIPT;path.parent.mkdir(parents=True);path.write_text(json.dumps(receipt))
            explain.verify_build(root,record)
            alternate=root/explain.PACKAGE/'root/bld/lib/libebm.so';alternate.write_bytes(b'other')
            with self.assertRaises(VerdugoError):explain.verify_build(root,record)
            alternate.unlink();(root/explain.PACKAGE/explain.BUILD_FILES[0]).write_bytes(b'changed')
            with self.assertRaises(VerdugoError):explain.verify_build(root,record)

    def test_unprepared_profile_does_not_import_or_install(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(explain,'home',return_value=Path(temp)):
            self.assertFalse(explain.runtime_state('interpret')['version_matches'])
