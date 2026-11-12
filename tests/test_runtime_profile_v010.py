import os
from pathlib import Path
import sys
import tempfile
import unittest
import venv
from unittest.mock import patch

from verdugo import runtime_profile
from verdugo.common import VerdugoError


class RuntimeProfileTests(unittest.TestCase):
    def test_no_profile_uses_current_interpreter(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(sys.executable, runtime_profile.interpreter('ragas'))
            self.assertEqual(sys.executable, runtime_profile.interpreter('haystack'))
            self.assertEqual(64, len(runtime_profile.binding('ragas')))

    def test_invalid_profile_is_never_executed(self):
        for value in ('', 'python', '/bin/sh', '/tmp/../bin/python', '/bin/python\n'):
            with self.subTest(value=value), patch.dict(os.environ, {'VERDUGO_RAGAS_PYTHON': value}):
                with self.assertRaises(VerdugoError):
                    runtime_profile.interpreter('ragas')

    def test_profile_cannot_redirect_other_services(self):
        with patch.dict(os.environ, {'VERDUGO_RAGAS_PYTHON': '/missing/python'}):
            self.assertEqual(sys.executable, runtime_profile.interpreter('haystack'))
            self.assertEqual(sys.executable, runtime_profile.interpreter('langgraph'))

    def test_missing_profile_fails_closed(self):
        with patch.dict(os.environ, {'VERDUGO_RAGAS_PYTHON': '/missing/profile/bin/python'}):
            with self.assertRaises(VerdugoError):
                runtime_profile.versions('ragas', ['ragas'])

    def test_venv_probe_and_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'profile'
            venv.EnvBuilder(with_pip=False).create(root)
            binary = str(root / 'bin' / 'python')
            with patch.dict(os.environ, {'VERDUGO_RAGAS_PYTHON': binary}):
                result = runtime_profile.versions('ragas', ['verdugo-test-nonexistent-distribution'])
                self.assertIsNone(result['verdugo-test-nonexistent-distribution'])
                before = runtime_profile.binding('ragas')
                with (root / 'pyvenv.cfg').open('a') as f:
                    f.write('\n# changed profile\n')
                self.assertNotEqual(before, runtime_profile.binding('ragas'))

    def test_world_writable_venv_configuration_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'profile'
            venv.EnvBuilder(with_pip=False).create(root)
            (root / 'pyvenv.cfg').chmod(0o666)
            with patch.dict(os.environ, {'VERDUGO_RAGAS_PYTHON': str(root/'bin'/'python')}):
                with self.assertRaises(VerdugoError):
                    runtime_profile.interpreter('ragas')
