"""Original servers reject missing TCP credentials and stop before returning."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verdugo import local_database as db
from database_fixtures import CASES, assert_result


class DatabaseProcesses(unittest.TestCase):
    def test_original_servers_stop_and_loopback_requires_credentials(self):
        selected=set(filter(None,os.getenv('VERDUGO_RUNTIME_SERVICES','').split(',')))
        selected &= {'valkey','postgres'}
        if not selected:self.skipTest('Other runtime group selected')
        for sid in selected:
            if not db.runtime_state(sid)['version_matches']:
                if os.getenv('VERDUGO_RUNTIME_REQUIRED')=='1':self.fail('Missing database runtime')
                self.skipTest('Database runtime not prepared')
        original_popen,original_native=db.subprocess.Popen,db.native
        servers=[];rejected=[]
        def popen(args,*a,**kw):
            process=original_popen(args,*a,**kw)
            if Path(args[0]).name in ('valkey-server','postgres'):servers.append(process)
            return process
        def native(home,binary,args,env,data=None,timeout=35):
            if db.loopback() and (binary=='psql' or binary=='valkey-cli' and 'MSET' in args):
                unauth=dict(env)
                unauth.pop('VALKEYCLI_AUTH',None);unauth.pop('PGPASSWORD',None)
                if binary == 'psql':
                    with self.assertRaises(ValueError):original_native(home,binary,args,unauth,data,timeout)
                else:
                    # The original CLI can report a RESP error with exit 0.
                    # A successful subprocess is not successful authorization.
                    response=original_native(home,binary,args,unauth,data,timeout)
                    self.assertIn(b'NOAUTH',response);self.assertNotEqual(b'"OK"',response.strip())
                rejected.append(binary)
            return original_native(home,binary,args,env,data,timeout)
        before=Path.cwd()
        try:
            for sid in sorted(selected):
                with self.subTest(service=sid), tempfile.TemporaryDirectory() as temp:
                    os.chdir(temp)
                    with patch.object(db.subprocess,'Popen',popen),patch.object(db,'native',native):
                        value=db.run(sid,CASES[sid])
                    assert_result(self,sid,value)
                    self.assertTrue(all(p.poll() is not None for p in servers))
        finally:
            os.chdir(before)
        self.assertEqual(len(selected),len(servers))
        if db.loopback():self.assertEqual(len(selected),len(rejected))
