CASES={
 'mcp-agent':{'dataset':'demo','currency':'MXN','rows':[{'channel':'organic','spend_minor':50,'revenue_minor':200,'leads':4,'conversions':2}]},
 'nemo-guardrails':{'dataset':'demo','flows':[{'id':'report','request':'Request a report','response':'Report ready'}]},
}
def assert_result(test,sid,r):
 if sid=='mcp-agent':
  test.assertEqual({'spend_minor':50,'revenue_minor':200,'leads':4,'conversions':2},r['totals'])
  test.assertEqual(0,r['llm_calls']);test.assertEqual(0,r['remote_servers']);test.assertFalse(r['autonomous_agent'])
 elif sid=='nemo-guardrails':
  test.assertEqual(['report'],r['flow_ids']);test.assertEqual(1,r['compiled_flows'])
  test.assertEqual(1,r['user_intents']);test.assertEqual(1,r['bot_responses'])
  test.assertEqual(0,r['models_configured']);test.assertFalse(r['runtime_executed'])
