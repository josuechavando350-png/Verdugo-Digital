"""Completion cannot be inferred from root licenses or duplicated batch membership."""
import copy
import unittest
from unittest.mock import patch

from verdugo import integration_audit as audit
from verdugo.common import VerdugoError


class IntegrationAuditTests(unittest.TestCase):
    def test_offline_reconciliation_distinguishes_registration_and_completion(self):
        with patch('socket.socket', side_effect=AssertionError('network attempted')):
            result = audit.summary()
        self.assertEqual(688, result['unique_github_identities'])
        self.assertEqual(666, result['root_policy_allowed'])
        self.assertEqual(0, result['duplicate_identities'])
        self.assertEqual(5, result['historical_aliases_removed'])
        self.assertFalse(result['all_666_integrated'])
        self.assertFalse(result['distribution_license_closure_verified'])
        self.assertEqual(666, result['implemented_adapters'] + result['pending_adapters'] + result['construction_components'])
        self.assertEqual(result['new_implemented'], sum(x['implemented'] for x in result['original_batches']))
        self.assertEqual(12, len(result['existing_profile_review']['profiles']))
        self.assertEqual([('A', 164, 2), ('B', 163, 0)],
                         [(x['name'], x['size'], x['implemented']) for x in result['batches']])
        self.assertEqual(39, result['implemented_before_rebatch'])
        self.assertEqual(['meta-ads'], result['outside_batches_pending'])
        self.assertEqual(result['pending_adapters'],
                         sum(x['pending'] for x in result['batches']) + 1)

    def test_rebatch_rejects_duplicates_reordering_lost_or_recounted_members(self):
        read = audit.read_json
        mutations = [
            lambda d: d['rebatch']['batches'][0]['ids'].__setitem__(0, 'semantic-kernel'),
            lambda d: d['rebatch']['batches'][1]['ids'].__setitem__(0, 'metagpt'),
            lambda d: d['rebatch']['batches'][0]['ids'].reverse(),
            lambda d: d['rebatch']['batches'][0]['ids'].pop(),
            lambda d: d['rebatch']['batches'][0].update(size=163),
            lambda d: d['rebatch']['previously_implemented'].__setitem__(0, 'metagpt'),
            lambda d: d['rebatch']['previously_implemented'].append('candle'),
            lambda d: d['rebatch'].update(outside_batches_pending=[]),
            lambda d: d['subbatches'][0]['ids'].reverse(),
        ]
        for mutate in mutations:
            def corrupted(path, *args):
                document, digest = read(path, *args)
                if path.name == 'resume-666.json':
                    document = copy.deepcopy(document)
                    mutate(document)
                return document, digest
            with self.subTest(mutation=mutations.index(mutate)), \
                    patch.object(audit, 'read_json', side_effect=corrupted), self.assertRaises(VerdugoError):
                audit.summary()

    def test_new_completion_counts_only_in_its_fixed_batch(self):
        resume, _ = audit.read_json(audit.ROOT/'sources/resume-666.json')
        queue = audit.read_registry()['work_queue']
        done = set(resume['rebatch']['previously_implemented']) | {'candle', 'openrlhf'}
        batches = audit.continuation_batches(resume, queue, done)
        self.assertEqual([['candle'], ['openrlhf']], [x['implemented_ids'] for x in batches])
        self.assertEqual([163, 162], [x['pending'] for x in batches])

        # Even a coherent rewrite of every batch must not relabel a future
        # completion as one of the 39 completed before this continuation.
        corrupted = copy.deepcopy(resume)
        previous = set(corrupted['rebatch']['previously_implemented'])
        previous.remove('txtai')
        previous.add('candle')
        corrupted['rebatch']['previously_implemented'] = [r['id'] for r in queue if r['id'] in previous]
        remaining = [sid for group in corrupted['subbatches'] for sid in group['ids']
                     if sid not in previous] + [r['id'] for r in queue if r['batch'] == 2]
        corrupted['rebatch']['batches'][0]['ids'] = remaining[:164]
        corrupted['rebatch']['batches'][1]['ids'] = remaining[164:]
        with self.assertRaises(VerdugoError):
            audit.continuation_batches(corrupted, queue, done)

    def test_duplicate_resume_member_does_not_inflate_completion(self):
        read = audit.read_json
        def corrupted(path, *args):
            document, digest = read(path, *args)
            if path.name == 'resume-666.json':
                document = copy.deepcopy(document)
                document['subbatches'][1]['ids'][0] = document['subbatches'][0]['ids'][0]
            return document, digest
        with patch.object(audit, 'read_json', side_effect=corrupted), self.assertRaises(VerdugoError):
            audit.summary()

    def test_missing_review_is_an_error_not_implicitly_approved(self):
        read = audit.read_json
        def missing(path, *args):
            if path.name == 'review-runtime-next666.json':
                raise VerdugoError('missing evidence')
            return read(path, *args)
        with patch.object(audit, 'read_json', side_effect=missing), self.assertRaises(VerdugoError):
            audit.summary()
