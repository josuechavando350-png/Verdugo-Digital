"""Toy-model boundaries and pinned original-source checks; native acceptance separate."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_lens666 as lens
from verdugo.common import VerdugoError
from verdugo.registry666 import read_registry

CASE = {'dataset':'demo', 'symbol_ids':[1,3,4,2], 'intervention':'zero_residual'}


class Lens666Tests(unittest.TestCase):
    def test_rejects_models_callbacks_raw_text_and_non_synthetic_data(self):
        lens.validate('transformerlens','activations.check',CASE)
        for change in ({'dataset':'real'},{'model':'remote'},{'callback':'lambda x:x'},
                       {'text':'private'},{'intervention':'custom'}, {'symbol_ids':[]},
                       {'symbol_ids':[1]*7}):
            with self.subTest(change=change), self.assertRaises(VerdugoError):
                lens.validate('transformerlens','activations.check',CASE | change)
        with self.assertRaises(VerdugoError):
            lens.validate('transformerlens','model.load',CASE)

    def test_symbol_ids_reject_coercion_and_out_of_vocabulary_values(self):
        for value in (True,-1,16,1.0,'1',None):
            with self.subTest(value=value), self.assertRaises(VerdugoError):
                lens.validate('transformerlens','activations.check',CASE | {'symbol_ids':[1,value]})

    def test_source_pin_and_bounded_original_native_config(self):
        record=json.loads(lens.CONTRACT.read_text())
        source=next(r for r in read_registry()['records'] if r['id']=='transformerlens')
        self.assertEqual(source['commit_sha'],record['commit'])
        self.assertEqual(375,sum(bool(f['installed_path']) for f in record['files']))
        self.assertEqual(1,lens.CONFIG['n_layers'])
        self.assertEqual(16,lens.CONFIG['d_vocab'])
        self.assertEqual(8,lens.CONFIG['n_ctx'])
        self.assertIn('transformer_lens/model_bridge/sources/native/__init__.py',
                      {f['path'] for f in record['files']})

    def test_altered_installed_source_is_rejected_before_import(self):
        record=json.loads(lens.CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            changed=Path(tmp)/'changed.py';changed.write_text('# changed')
            with patch.object(lens.metadata,'distribution') as dist, \
                 patch.object(lens.metadata,'version',side_effect=record['runtime_versions'].__getitem__):
                dist.return_value.version='0.0.0'
                dist.return_value.locate_file.return_value=changed
                with self.assertRaises(VerdugoError):lens.verify_source()
