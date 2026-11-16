import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from verdugo import runtime_profile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('installer',ROOT/'scripts/instalar_perfiles.py')
installer=importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)

class InstallerTests(unittest.TestCase):
    def test_all_recognized_python_profiles_have_requirements_and_constraints(self):
        available=installer.profiles()
        variables={x[2] for x in available.values()}
        self.assertFalse(set(runtime_profile.PROFILE_ENV.values())-variables)
        self.assertIn('VERDUGO_RUNTIME_PYTHON',variables)
    def test_private_directory_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'private'; installer.private_dir(root)
            self.assertEqual(root.stat().st_mode&0o777,0o700)
            link=Path(temp)/'link';link.symlink_to(root)
            with self.assertRaises(RuntimeError): installer.private_dir(link)
    def test_installer_is_never_automatic(self):
        config=json.loads((ROOT/'.devcontainer/devcontainer.json').read_text())
        self.assertNotIn('--perfiles',config['postCreateCommand'])
        from verdugo.mcp import tool_definitions
        self.assertFalse(any('install' in x['name'] or 'profile' in x['name'] for x in tool_definitions()))
    def test_mcp_examples_start_stdio_without_shell(self):
        cfg=json.loads((ROOT/'.mcp.json').read_text())['mcpServers']['verdugo']
        self.assertEqual(cfg['type'],'stdio'); self.assertEqual(cfg['command'],'python'); self.assertEqual(cfg['args'][-1],'mcp')
        import tomllib
        codex=tomllib.loads((ROOT/'examples/codex-config.toml').read_text())['mcp_servers']['verdugo']
        self.assertEqual(codex['args'],cfg['args'])
