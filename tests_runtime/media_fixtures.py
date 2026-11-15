CASES={
 'quarto':{'dataset':'demo','title':'Informe de prueba','sections':[{'heading':'Observaciones','text':'Solo texto; sin ejecutar código.'},{'heading':'Límites','text':'No demuestra resultados comerciales.'}]},
 'auto-editor':{'dataset':'demo','samples':[0.]*4000+[.5]*4000},
}
def assert_result(t,sid,r):
 if sid=='quarto':
  t.assertEqual(2,r['sections']);t.assertIn('Informe de prueba</h1>',r['html']);t.assertIn('Observaciones</h2>',r['html']);t.assertIn('Solo texto; sin ejecutar código.',r['html']);t.assertFalse(r['code_executed']);t.assertFalse(r['remote_assets_fetched'])
 else:
  t.assertEqual(10,len(r['levels']));t.assertEqual([0.]*5,r['levels'][:5])
  for value in r['levels'][5:]:t.assertAlmostEqual(.5,value,places=4)
  t.assertEqual(8000,r['samples']);t.assertFalse(r['audio_edited']);t.assertFalse(r['speech_transcribed'])
