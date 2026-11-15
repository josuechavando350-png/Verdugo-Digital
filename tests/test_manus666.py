"""Public input and original-source boundaries, without mocking SDK execution."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from verdugo.common import VerdugoError
from verdugo import local_manus666 as manus
from verdugo.registry666 import read_registry


class Manus666Tests(unittest.TestCase):
    def test_only_fixed_statuses_and_demo_data_enter_the_original_tool(self):
        base = {'dataset': 'demo', 'statuses': ['completed'] * 5}
        manus.validate('openmanus', 'stages.track', base)
        for change in ({'dataset':'real'}, {'statuses':['completed']*6},
                       {'statuses':['approved']*5}, {'statuses':[True]*5},
                       {'command':'bash'}, {'api_key':'secret'}, {'path':'/tmp'}):
            with self.subTest(change=change), self.assertRaises(VerdugoError):
                manus.validate('openmanus', 'stages.track', base | change)

    def test_archive_with_different_bytes_is_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'share/verdugo-openmanus/source.tar.gz'
            p.parent.mkdir(parents=True);p.write_bytes(b'changed')
            with patch.object(manus.sys, 'prefix', tmp), self.assertRaises(VerdugoError):
                manus.source_archive()

    def test_archive_cannot_add_unreviewed_files_or_paths(self):
        for path in ('upstream/app/../../escape.py', 'upstream/app/extra.py'):
            data=io.BytesIO()
            with tarfile.open(fileobj=data,mode='w:gz') as archive:
                member=tarfile.TarInfo(path);member.size=1
                archive.addfile(member,io.BytesIO(b'x'))
            with tempfile.TemporaryDirectory() as tmp, self.assertRaises(VerdugoError):
                manus.extract_original(data.getvalue(), {'source_files':[]}, Path(tmp))

    def test_original_source_contract_matches_catalog_commit_and_has_no_provider(self):
        contract=json.loads(manus.CONTRACT.read_text())
        registered=next(r for r in read_registry()['records'] if r['id']=='openmanus')
        self.assertEqual(registered['commit_sha'],contract['commit'])
        self.assertEqual(82,contract['original_source_files_verified'])
        self.assertEqual(84,len({r['path'] for r in contract['source_files']}))
        self.assertNotIn('https://',manus.EMPTY_CONFIG)
        self.assertIn('api_key=""',manus.EMPTY_CONFIG)

