import json
import unittest
from verdugo import local_images,local_lastnode
from verdugo.common import VerdugoError
class LastOriginals(unittest.TestCase):
 def test_private_image_content_cannot_select_paths_images_cloud_or_commands(self):
  p={'dataset':'demo','secret_text':json.dumps(['Supplied text'])};local_images.validate('microsandbox','image.inspect',p)
  for key in ['path','url','image','command','cloud','token','archive']:
   with self.assertRaises(VerdugoError):local_images.validate('microsandbox','image.inspect',p|{key:'forbidden'})
  for value in [[],['x']*21,[{'path':'/etc/passwd','text':'bad'}],['x'*1001]]:
   with self.assertRaises(VerdugoError):local_images.validate('microsandbox','image.inspect',p|{'secret_text':json.dumps(value)})
 def test_landscape_adaptation_changes_only_the_private_report_path(self):
  original=(local_lastnode.SOURCE/'reporter.original.js').read_bytes();adapted=(local_lastnode.SOURCE/'reporter.js').read_bytes()
  self.assertEqual(2,original.count(b"'/tmp/landscape.json'"));self.assertEqual(original.replace(b"'/tmp/landscape.json'",b"'landscape-errors.json'"),adapted)
 def test_landscape_fields_cannot_select_code_settings_or_communication(self):
  p={'dataset':'demo','secret_text':json.dumps([{'name':'Supplied'}])};local_lastnode.validate('landscape-app','landscape.validate',p)
  for key in ['path','url','command','settings','token','github_token']:
   with self.assertRaises(VerdugoError):local_lastnode.validate('landscape-app','landscape.validate',p|{key:'forbidden'})
  for row in [{'name':'Supplied','__proto__':{}},{'name':'Supplied','repo_url':{}},{'name':'Supplied','script':'exec'}]:
   with self.assertRaises(VerdugoError):local_lastnode.validate('landscape-app','landscape.validate',p|{'secret_text':json.dumps([row])})

 def test_mcp_cannot_select_urls_html_tools_or_browser_configuration(self):
  doc={'title':'Supplied','headings':[{'level':1,'text':'Heading'}],'buttons':[]}
  p={'dataset':'demo','secret_text':json.dumps(doc)}
  local_lastnode.validate('playwright-mcp','document.snapshot',p)
  for key in ['url','html','tool','command','browser','config','path','token']:
   with self.subTest(key=key),self.assertRaises(VerdugoError):local_lastnode.validate('playwright-mcp','document.snapshot',p|{key:'forbidden'})
   with self.subTest(nested=key),self.assertRaises(VerdugoError):local_lastnode.validate('playwright-mcp','document.snapshot',p|{'secret_text':json.dumps(doc|{key:'forbidden'})})
  for bad in [[],{},doc|{'headings':[]},doc|{'headings':[{'level':True,'text':'x'}]},doc|{'headings':[{'level':7,'text':'x'}]},doc|{'headings':[{'level':1,'text':'x','onclick':'bad'}]},doc|{'buttons':['x']*21},doc|{'title':'x'*161}]:
   with self.subTest(value=bad),self.assertRaises(VerdugoError):local_lastnode.validate('playwright-mcp','document.snapshot',p|{'secret_text':json.dumps(bad)})
  with self.assertRaises(VerdugoError):local_lastnode.validate('playwright-mcp','browser_navigate',p)
