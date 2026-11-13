"""Source pin contracts are not proof that the fifty applications are installed."""
import configparser
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
class PortfolioSourcePins(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((ROOT/'stack/portfolio50.json').read_text())
        cls.lock=json.loads((ROOT/'stack/portfolio-pins.json').read_text())
        cls.config=configparser.ConfigParser();cls.config.read(ROOT/'.gitmodules')

    def test_fifty_exact_pins_without_relabeling_legacy(self):
        expected={m['id'] for m in self.catalog['modules']}
        self.assertEqual(len(expected),50)
        self.assertEqual(set(self.lock['pins']),expected)
        self.assertFalse(self.lock['all_fifty_integrated'])
        self.assertFalse(self.lock['production_ready'])
        self.assertEqual(len(self.catalog['retained_originals']),6)
        self.assertEqual(len(self.config.sections()),54)
        self.assertEqual(set(self.catalog['legacy_preserved']),{'countly','dittofeed','erxes','openreplay'})

    def test_original_urls_and_immutable_shas(self):
        retained=set(self.catalog['retained_originals'])
        for module in self.catalog['modules']:
            ident=module['id'];path=('upstream/' if ident in retained else 'components/')+ident
            section='submodule "'+path+'"'
            with self.subTest(module=ident):
                self.assertIn(section,self.config)
                self.assertEqual(self.config[section]['path'],path)
                self.assertEqual(self.config[section]['url'],'https://github.com/'+module['repository']+'.git')
                self.assertRegex(self.lock['pins'][ident],r'^[0-9a-f]{40}$')
        self.assertEqual(len({self.config[s]['url'].lower() for s in self.config.sections()}),54)

    @unittest.skipUnless(shutil.which('git') and (ROOT/'.git').exists(),'Git checkout required')
    def test_committed_gitlinks_match_all_fifty_selected_pins(self):
        entries={}
        for prefix,count in [('upstream',10),('components',44)]:
            output=subprocess.check_output(['git','ls-tree','HEAD:'+prefix],cwd=ROOT,text=True)
            rows=output.splitlines();self.assertEqual(len(rows),count)
            for row in rows:
                meta,name=row.split('\t',1);mode,kind,sha=meta.split()
                self.assertEqual((mode,kind),('160000','commit'))
                entries[prefix+'/'+name]=sha
        retained=set(self.catalog['retained_originals'])
        for ident,sha in self.lock['pins'].items():
            path=('upstream/' if ident in retained else 'components/')+ident
            self.assertEqual(entries[path],sha)

if __name__=='__main__':unittest.main()
