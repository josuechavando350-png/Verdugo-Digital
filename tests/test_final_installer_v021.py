"""Integrity after original Grype hydration is specific to an installation."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from install_final import DB_SHA, DB_URL, grype_import_binding

class GrypeImportBinding(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.db=self.home/'grype-db/6'
        self.db.mkdir(parents=True)
        self.metadata={'source':DB_URL+'?checksum=sha256%3A'+DB_SHA,
                       'client_version':'v6.1.10','digest':'xxh64:0123456789abcdef'}
        (self.db/'import.json').write_text(json.dumps(self.metadata))
        (self.db/'vulnerability.db').write_bytes(b'synthetic hydrated SQLite bytes')

    def test_archive_provenance_and_hydrated_hash_are_distinct(self):
        binding=grype_import_binding(self.home)
        self.assertEqual(DB_SHA,binding['database_archive_sha256'])
        self.assertEqual(self.metadata['source'],binding['database_source'])
        self.assertEqual(hashlib.sha256(b'synthetic hydrated SQLite bytes').hexdigest(),binding['database_sha256'])
        self.assertNotEqual(binding['database_archive_sha256'],binding['database_sha256'])

    def test_wrong_source_or_client_does_not_get_a_binding(self):
        for change in ({'source':'https://outside.invalid/snapshot'}, {'client_version':'v5.0.0'}, {'digest':None}):
            (self.db/'import.json').write_text(json.dumps(dict(self.metadata,**change)))
            with self.assertRaises(ValueError):grype_import_binding(self.home)

    def test_modified_hydrated_bytes_change_the_binding(self):
        before=grype_import_binding(self.home)
        (self.db/'vulnerability.db').write_bytes(b'different physical layout')
        after=grype_import_binding(self.home)
        self.assertNotEqual(before['database_sha256'],after['database_sha256'])
        self.assertEqual(before['database_archive_sha256'],after['database_archive_sha256'])

    def test_missing_import_metadata_is_not_accepted(self):
        (self.db/'import.json').unlink()
        with self.assertRaises(OSError):grype_import_binding(self.home)
