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
