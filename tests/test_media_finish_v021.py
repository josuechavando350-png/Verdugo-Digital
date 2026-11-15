import copy
import sys
from pathlib import Path
import unittest
from verdugo import local_media
from verdugo.common import VerdugoError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests_runtime'))
from media_fixtures import CASES
class MediaFinish(unittest.TestCase):
 def test_bounded_plain_text_and_pcm_reject_paths_commands_and_nonfinite_numbers(self):
  for sid,p in CASES.items():
   op=local_media.SPECS[sid][0];local_media.validate(sid,op,p)
   for key in ('url','command','path','format','execute','filters','output','sample_rate'):
    with self.assertRaises(VerdugoError):local_media.validate(sid,op,p|{key:'forbidden'})
  for value in (float('nan'),float('inf'),True,1.1,-1.1):
   p=copy.deepcopy(CASES['auto-editor']);p['samples'][0]=value
   with self.assertRaises(VerdugoError):local_media.validate('auto-editor','audio.levels',p)
  for samples in ([0.]*799,[0.]*8001):
   with self.assertRaises(VerdugoError):local_media.validate('auto-editor','audio.levels',{'dataset':'demo','samples':samples})
