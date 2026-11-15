"""Original implementations must preserve false assertions and supplied literals."""
from contextlib import closing
import os
import unittest

from verdugo import local_runtime
from verdugo.__main__ import template
from verdugo.engine import Engine


class FinalEdges(unittest.TestCase):
    def test_promptfoo_false_assertion_and_literal_response(self):
        selected = set(filter(None, os.getenv('VERDUGO_RUNTIME_SERVICES', '').split(',')))
        if selected and 'promptfoo' not in selected:
            self.skipTest('Other runtime group selected')
        if not local_runtime.installed('promptfoo')['version_matches']:
            if os.getenv('VERDUGO_RUNTIME_REQUIRED') == '1':
                self.fail('Missing required Promptfoo runtime')
            self.skipTest('Original Promptfoo not installed')
        cfg = template('nexus')
        cfg['tenants']['nexus']['services']['promptfoo'].update(enabled=True, license_reviewed=True, runtime_reviewed=True)
        with closing(Engine(':memory:', cfg)) as engine:
            for number, text, terms, expected in (
                (1, 'solar report', ['wind'], False),
                (2, '{{ 7 * 7 }}', ['49'], False),
                (3, '{{ 7 * 7 }}', ['7'], True),
                (4, 'file:///nonexistent/verdugo-marker', ['marker'], True),
            ):
                with self.subTest(case=number):
                    result = engine.execute({'service':'promptfoo', 'operation':'response.check',
                        'key':'evaluation-'+str(number), 'params':{'dataset':'demo','text':text,'required_terms':terms}}, True)
                    self.assertEqual('succeeded', result['state'], result)
                    value = result['result']['result']
                    self.assertEqual(expected, value['passed'])
                    self.assertEqual(int(expected), value['score'])
                    self.assertEqual(0, value['llm_calls'])
