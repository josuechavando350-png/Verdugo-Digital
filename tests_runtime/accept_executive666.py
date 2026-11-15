"""Run the original executive SDKs together and resume through the same CLI/MCP/SQLite."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from verdugo.__main__ import template
from verdugo.engine import Engine
from verdugo.mcp import invoke
from verdugo import local_runtime, objectives, workflow


def accept():
    services=('semantic-kernel','agno','ag2','langroid','griptape','beeai-framework','harness-sdk','unified-planning','voltagent','servers','monty','playwright-python','hatchet','invariant','pyrit','llama-cpp','granite-guardian','interpret','transformerlens','bitsandbytes','guidance','lm-format-enforcer','usearch','rerankers','sympy','rdflib','z3','txtai')
    spec=json.loads((ROOT/'examples/executive666.synthetic.json').read_text())
    cfg=template('nexus')
    for sid in services:
        assert local_runtime.installed(sid)['version_matches'],sid
        cfg['tenants']['nexus']['services'][sid].update(
            enabled=True,license_reviewed=True,runtime_reviewed=True,timeout_seconds=60)
    calls=[]
    with tempfile.TemporaryDirectory(prefix='verdugo-executive666-') as tmp:
        state=str(Path(tmp)/'state.sqlite3')
        config=Path(tmp)/'config.json';config.write_text(json.dumps(cfg));config.chmod(0o600)
        def engine(**kw):return Engine(state,cfg,transport=lambda *a:calls.append(a),**kw)
        with closing(engine()) as e:
            preview=invoke(e,'verdugo_workflow',{'workflow':spec})
            assert len(preview['approval_batch'])==1
            paused=workflow.run(e,spec,True)
            assert paused['state']=='paused' and paused['step']=='simulate',paused
            assert paused['outcome']['state']=='awaiting_approval'
        with closing(engine(role='approver',actor='synthetic-reviewer')) as e:
            e.approve_many(preview['approval_batch'])
        with closing(engine()) as e:
            result=invoke(e,'verdugo_workflow',{'workflow':spec,'execute':True})
            assert result['state']=='succeeded',result
            assert set(result['steps'])=={'kernel','agno','check','simulate','measure','claims','scenarios','review','parallel','sequence','measurement_review','memory','monty','cookie_state','dispatch_policy','trace_policy','tool_audit','context_budget','model_review','explanation','activations','quantization','schema_check','prefix_check','neighbors_check','ranked_results','polynomial_check','reachability_check','constraints_check','content_reconcile'}
            r=result['steps']['check']['result']
            assert r['planned_contacts']==200 and r['planned_cost_minor']==0
            assert r['feasible_under_declared_limits'] and not r['external_execution_authorized']
            assert result['steps']['agno']['result']['budget_checked']
            for step,sid in zip(('kernel','agno','check','claims','scenarios','review','parallel','sequence','measurement_review','memory','monty','cookie_state','dispatch_policy','trace_policy','tool_audit','context_budget','model_review','explanation','activations','quantization','schema_check','prefix_check','neighbors_check','ranked_results','polynomial_check','reachability_check','constraints_check','content_reconcile'),services):
                actual=result['steps'][step]['result']
                assert actual['original_sdk']==sid and actual['llm_calls']==(1 if sid=='granite-guardian' else 0)
                assert not actual['autonomous_agent']
            assert all(c['verdict']=='contradicted' for c in result['steps']['claims']['result']['claims'])
            assert result['steps']['scenarios']['result']['pareto_nondominated_indices']==[0]
            assert result['steps']['review']['result']['recommendation']=='revise_strategy'
            assert result['steps']['parallel']['result']['recommendation']=='request_operator_review'
            assert result['steps']['sequence']['result']['sequence_valid']
            assert result['steps']['measurement_review']['result']['review_recommendation']=='review_shortfall'
            assert result['steps']['memory']['result']['matching_incident_relation_count']==2
            assert result['steps']['memory']['result']['duplicate_relations_skipped']==1
            assert result['steps']['memory']['result']['temporary_server_restart_verified']
            assert result['steps']['memory']['result']['sdk_graph_deleted']
            assert 'stage_0' not in '\n'.join(e.db.iterdump())
            assert result['steps']['monty']['result']['planned_cost_minor']==0
            assert result['steps']['monty']['result']['within_budget']
            assert result['steps']['monty']['result']['native_artifact_receipt_verified']
            assert result['steps']['cookie_state']['result']['retained_cookie_count']==2
            assert result['steps']['cookie_state']['result']['fresh_context_isolated']
            assert 'fixed-demo-value' not in '\n'.join(e.db.iterdump())
            assert 'synthetic_0' not in '\n'.join(e.db.iterdump())
            policy = result['steps']['dispatch_policy']['result']
            assert policy['compiled_retries']==0 and policy['reconciliation_required']
            assert policy['compiled_max_parallel']==2 and policy['protobuf_round_trip_verified']
            assert policy['compiled_idempotency_method']=='STATUS'
            assert policy['dispatch_policy_draft_only'] and not policy['server_policy_enforced']
            assert policy['tasks_dispatched']==0 and policy['approvals_granted']==0
            trace = result['steps']['trace_policy']['result']
            assert trace['rule_match_counts']=={'review_missing':1,'reconcile_first':1,'private_before_send':1}
            assert trace['rule_match_count']==3 and trace['matches_require_review']
            assert trace['tool_calls_executed']==0 and trace['approvals_granted']==0
            assert trace['ordered_pattern_only'] and not trace['data_leak_proven']
            assert 'fixed_trace_0' not in '\n'.join(e.db.iterdump())
            tool_audit = result['steps']['tool_audit']['result']
            assert tool_audit['message_links_valid']
            assert tool_audit['recorded_invoked_tool_kind_count']==1
            assert tool_audit['synthetic_piece_count']==6
            assert tool_audit['tool_calls_executed']==0 and tool_audit['approvals_granted']==0
            assert not tool_audit['absence_proves_nonexecution']
            assert not tool_audit['successful_completion_proven']
            assert 'fixed_pyrit_call_' not in '\n'.join(e.db.iterdump())
            tokens = result['steps']['context_budget']['result']
            model = result['steps']['model_review']['result']
            assert tokens['fits_context'] and tokens['input_units']==229
            assert not tokens['model_weights_loaded_for_inference'] and tokens['llm_calls']==0
            assert model['model_says_unsupported'] and model['agrees_with_synthetic_reference']
            assert model['llm_calls']==1 and model['model_weights_loaded_for_inference']
            assert model['prompt_sha256']==tokens['prompt_sha256']
            assert not model['quality_calibrated'] and not model['probability_estimated']
            assert not model['external_execution_authorized'] and model['approvals_granted']==0
            assert 'The synthetic plan has a budget' not in '\n'.join(e.db.iterdump())
            assert '<confidence>' not in '\n'.join(e.db.iterdump())
            explanation=result['steps']['explanation']['result']
            assert explanation['additive_reconstruction_verified']
            assert explanation['feature_count']==2 and explanation['term_count']==2
            assert explanation['training_row_count']==16 and explanation['query_row_count']==2
            assert explanation['max_additive_reconstruction_error']<1e-12
            assert not explanation['held_out_accuracy_measured'] and not explanation['causal_explanation_proven']
            assert not explanation['model_persisted'] and explanation['approvals_granted']==0
            activation=result['steps']['activations']['result']
            assert activation['hooks_removed_and_output_restored'] and activation['hooks_remaining']==0
            assert activation['max_output_change']>0 and activation['max_restored_output_error']==0
            assert activation['toy_model_parameter_count']==936 and activation['toy_forward_passes']==3
            assert activation['max_attention_row_sum_error']<1e-6 and activation['max_future_attention']==0
            assert activation['untrained_toy_model'] and not activation['pretrained_weights_downloaded']
            assert not activation['real_llm_reasoning_explained'] and activation['approvals_granted']==0
            assert 'logits' not in activation and 'activations' not in activation
            quantized=result['steps']['quantization']['result']
            assert quantized['native_cpu_path_used'] and quantized['block_scales_verified']
            assert quantized['original_array_bytes']==256 and quantized['quantized_array_bytes']==64
            assert quantized['codebook_array_bytes']==1024 and quantized['scale_array_bytes']==4
            assert quantized['total_representation_array_bytes']==1092 and quantized['array_bytes_saved']==-836
            assert quantized['scalar_reconstruction_max_error']<1e-4 and not quantized['speed_benchmarked']
            shape=result['steps']['schema_check']['result']
            assert shape['native_parser_used'] and shape['independent_enum_reference_verified']
            assert shape['accepted_indices']==[0] and shape['rejected_count']==2
            assert shape['parser_threads_remaining']==0 and not shape['syntactic_validity_grants_permission']
            assert not shape['raw_payloads_persisted']
            prefix=result['steps']['prefix_check']['result']
            assert prefix['viable_indices']==[0,1] and prefix['complete_indices']==[0]
            assert prefix['first_rejection_offsets']==[None,None,13]
            assert prefix['independent_finite_language_verified']
            assert not prefix['syntactic_validity_grants_permission']
            neighbors=result['steps']['neighbors_check']['result']
            assert neighbors['independent_scalar_reference_verified'] and neighbors['native_cpu_path_used']
            assert neighbors['vectors_indexed']==5 and neighbors['graph_entries_reachable']==5
            assert neighbors['walk_matches_checked']==9 and neighbors['scan_matches_checked']==9
            assert neighbors['walk_distance_max_error']<1e-4 and not neighbors['corpus_recall_measured']
            ranked=result['steps']['ranked_results']['result']
            assert ranked['selected_indices']==[1,2,0] and ranked['missing_value_count']==1
            assert ranked['independent_numeric_order_verified'] and not ranked['scores_computed_by_model']
            assert ranked['model_backends_initialized']==0
            polynomial=result['steps']['polynomial_check']['result']
            assert polynomial['evaluations']==[1,0,4] and polynomial['derivative_evaluations']==[-2,0,4]
            assert polynomial['factor_multiplicities']==[2] and polynomial['independent_factor_product_verified']
            graph=result['steps']['reachability_check']['result']
            assert graph['reachable_indices']==[0,1,2] and graph['unique_edges']==3 and graph['duplicate_edges']==1
            assert graph['independent_closure_verified'] and graph['remote_graphs_loaded']==0
            constraints=result['steps']['constraints_check']['result']
            assert constraints['verdict']=='sat' and constraints['native_witness_units']==[1,1,0]
            assert constraints['feasible_assignments']==1 and constraints['finite_reference_verified']
            content=result['steps']['content_reconcile']['result']
            assert content['remaining_count']==2 and content['repeated_deletion_verified']
            assert content['after_groups']==[{'segment':0,'total':result['steps']['measure']['observed_contacts'],'records':1},
                                              {'segment':1,'total':result['steps']['measure']['observed_clients'],'records':1}]
            assert 'fixed_synthetic_content' not in '\n'.join(e.db.iterdump())
            assert e.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]==30
        with closing(engine()) as e, \
                patch.object(local_runtime,'execute',side_effect=AssertionError('SDK re-executed')), \
                patch.object(objectives,'simulate',side_effect=AssertionError('simulation re-executed')):
            replay=workflow.run(e,spec,True)
            assert replay['state']=='succeeded' and replay['steps']==result['steps']
        proc=subprocess.run([sys.executable,'-m','verdugo','--config',str(config),'--state',state,
                             'workflow','@'+str(ROOT/'examples/executive666.synthetic.json'),'--execute'],
                            cwd=ROOT,capture_output=True,text=True,timeout=180)
        assert proc.returncode==0,proc.stderr
        assert json.loads(proc.stdout)['state']=='succeeded'
        with closing(engine()) as e:
            rejected=e.execute({'service':'ag2','operation':'actions.check','key':'over-budget',
                'params':{'dataset':'demo','currency':'MXN','budget_minor':50,
                          'actions':[{'channel':'referral','contacts':10,'cost_per_contact_minor':6}]}},True)
            assert rejected['state']=='succeeded',rejected
            data=rejected['result']['result']
            assert data['planned_cost_minor']==60 and not data['within_budget']
            assert not data['feasible_under_declared_limits'] and not data['external_execution_authorized']
            for key,changes,wanted in [('limits',{'budget_ok':False},'revise_limits'),
                                      ('capacity',{'capacity_ok':False},'revise_limits'),
                                      ('ready',{'observed_clients':20},'request_operator_review')]:
                params={'dataset':'demo','budget_ok':True,'capacity_ok':True,'observed_clients':17,'target_clients':20}|changes
                branch=e.execute({'service':'beeai-framework','operation':'review.route','key':'branch-'+key,'params':params},True)
                assert branch['state']=='succeeded',branch
                b=branch['result']['result']
                assert b['recommendation']==wanted and b['operator_approval_required']
                assert not b['external_execution_authorized']
            from planning666_fixtures import CASES
            negative_process_cases = []
            for key, changes, reason, failed in [
                ('skip-review', {'sequence':['plan','limits','simulate','measure']}, 'inapplicable_action', 'simulate'),
                ('repeat-plan', {'sequence':['plan','plan']}, 'inapplicable_action', 'plan'),
                ('empty', {'sequence':[]}, 'unsatisfied_goals', None),
                ('limits-false', {'limits_satisfied':False}, 'inapplicable_action', 'limits'),
                ('review-unavailable', {'hypothetical_review_available':False}, 'inapplicable_action', 'operator_review')]:
                check=e.execute({'service':'unified-planning','operation':'sequence.validate','key':'formal-'+key,
                                 'params':dict(CASES['unified-planning'],**changes)},True)
                assert check['state']=='succeeded',check
                checked=check['result']['result']
                assert not checked['sequence_valid'] and checked['reason']==reason
                assert checked['first_inapplicable_stage']==failed
                assert checked['approvals_granted']==0 and not checked['operator_approval_verified']
                negative_process_cases.append({'case':key,'reason':reason,'failed_stage':failed})
            for key,capacity,budget,wanted in [('over-budget',20,50,'revise_limits'),
                                             ('over-capacity',5,100,'revise_limits'),
                                             ('within-limits',20,100,'request_operator_review')]:
                check=e.execute({'service':'harness-sdk','operation':'limits.parallel','key':'graph-'+key,
                                 'params':dict(CASES['harness-sdk'],capacity_contacts=capacity,budget_minor=budget)},True)
                assert check['state']=='succeeded',check
                checked=check['result']['result']
                assert checked['recommendation']==wanted and checked['approvals_granted']==0
            check=e.execute({'service':'voltagent','operation':'measurement.review','key':'review-target-met',
                             'params':dict(CASES['voltagent'],observed_clients=20)},True)
            assert check['state']=='succeeded',check
            assert check['result']['result']['review_recommendation']=='review_before_execution'
            assert not check['result']['result']['external_execution_authorized']
            check=e.execute({'service':'servers','operation':'graph.audit','key':'memory-no-matches',
                             'params':{'dataset':'demo','statuses':['completed'],'edges':[],'query':'blocked'}},True)
            assert check['state']=='succeeded',check
            graph=check['result']['result']
            assert graph['entity_count']==1 and graph['matching_entity_count']==0
            assert graph['unique_relation_count']==0 and graph['matching_incident_relation_count']==0
            assert graph['sdk_graph_deleted'] and not graph['durable_agent_memory']
            for key,budget,capacity,within_budget,within_capacity in [
                ('over-budget',50,20,False,True),('over-capacity',100,5,True,False),
                ('exact',60,10,True,True)]:
                checked=e.execute({'service':'monty','operation':'budget.evaluate','key':'native-'+key,
                    'params':dict(CASES['monty'],budget_minor=budget,capacity_contacts=capacity)},True)
                assert checked['state']=='succeeded',checked
                native=checked['result']['result']
                assert native['planned_cost_minor']==60 and native['planned_contacts']==10
                assert native['within_budget']==within_budget and native['within_capacity']==within_capacity
                assert native['approvals_granted']==0 and not native['arbitrary_code_accepted']
            cookie=CASES['playwright-python']['cookies'][0]
            for key,last,expected in [('expired',dict(cookie,lifetime='expired'),0),
                                      ('replaced',dict(cookie,secure=False,http_only=False),1)]:
                checked=e.execute({'service':'playwright-python','operation':'cookies.check','key':'cookies-'+key,
                    'params':{'dataset':'demo','cookies':[cookie,last]}},True)
                assert checked['state']=='succeeded',checked
                state=checked['result']['result']
                assert state['retained_cookie_count']==expected and state['secure_cookie_count']==0
                assert state['fresh_context_isolated'] and state['sdk_contexts_disposed']
                assert state['http_requests_made']==0 and state['browsers_launched']==0
            for kind, previous, expected in [('read','failed',3),('read','running',0),
                                             ('read','uncertain',0),('write','failed',0)]:
                params={'dataset':'demo','operation_kind':kind,'previous_state':previous,
                        'max_parallel':4,'requested_retries':3,'timeout_seconds':5,
                        'retention_seconds':60}
                checked=e.execute({'service':'hatchet','operation':'policy.compile',
                    'key':'policy-'+kind+'-'+previous,'params':params},True)
                assert checked['state']=='succeeded',checked
                policy=checked['result']['result']
                assert policy['compiled_retries']==expected and policy['fallback_retention_ms']==60000
                assert policy['compiled_execution_timeout_seconds']==5
                assert policy['compiled_schedule_timeout_seconds']==120
                assert policy['compiled_strategy']=='GROUP_ROUND_ROBIN'
                assert policy['reconciliation_required']==(previous in ('running','uncertain'))
                assert policy['retries_executed']==0 and not policy['external_execution_authorized']
            # Original parser/evaluator, including reversed ordering, false
            # hypothetical review, uncertain retry and multiple ordered pairs.
            trace_cases = [
                (['read_public','send'], 'failed', True, (0,0,0)),
                (['send','read_private'], 'failed', True, (0,0,0)),
                (['read_private','send'], 'failed', True, (0,0,1)),
                (['send'], 'failed', False, (1,0,0)),
                (['send'], 'running', True, (0,1,0)),
                (['send'], 'uncertain', True, (0,1,0)),
                (['read_private','draft','read_private','send','send'], 'failed', True, (0,0,4))]
            for index, (kinds, previous, reviewed, expected) in enumerate(trace_cases):
                checked=e.execute({'service':'invariant','operation':'trace.check',
                    'key':'trace-case-'+str(index),'params':{'dataset':'demo','events':[
                        {'kind':kind,'previous_state':previous,'hypothetical_review':reviewed}
                        for kind in kinds]}},True)
                assert checked['state']=='succeeded',checked
                trace=checked['result']['result']
                assert tuple(trace['rule_match_counts'][rule] for rule in
                    ('review_missing','reconcile_first','private_before_send'))==expected,trace
                assert trace['rule_match_count']==sum(expected)
                assert trace['approvals_granted']==0 and not trace['external_execution_authorized']
            for index, (fmt, outcome, simulated, valid, matches) in enumerate([
                ('chat','invoked',False,True,1), ('responses','invoked',False,True,1),
                ('chat','invoked',True,True,0), ('chat','missing',False,True,0),
                ('responses','not_invoked',False,True,0),
                ('responses','out_of_order',False,False,0),
                ('chat','duplicate_output',False,False,0),
                ('responses','unmatched_output',False,False,0)]):
                checked=e.execute({'service':'pyrit','operation':'tools.audit',
                    'key':'tool-audit-'+str(index),'params':{'dataset':'demo','calls':[
                        {'tool':'draft','format':fmt,'outcome':outcome,'simulated':simulated}]}},True)
                assert checked['state']=='succeeded',checked
                audited=checked['result']['result']
                assert audited['message_links_valid']==valid
                assert audited['recorded_invoked_tool_kind_count']==matches
                assert audited['tool_calls_executed']==0 and audited['approvals_granted']==0
            checked=e.execute({'service':'llama-cpp','operation':'tokens.check',
                'key':'context-too-small','params':{'dataset':'demo','context_budget_units':200,
                    'response_budget_units':900,'context_limit':200}},True)
            assert checked['state']=='succeeded',checked
            assert not checked['result']['result']['fits_context']
            assert checked['result']['result']['llm_calls']==0
            # Selected positive and negative controls, not an accuracy estimate.
            for key, response, expected in [('supported',200,False),('unsupported-repeat',900,True)]:
                checked=e.execute({'service':'granite-guardian','operation':'risk.assess',
                    'key':'model-'+key,'params':{'dataset':'demo','context_budget_units':200,
                        'response_budget_units':response}},True)
                assert checked['state']=='succeeded',checked
                observed=checked['result']['result']
                assert observed['model_says_unsupported']==expected,observed
                assert observed['agrees_with_synthetic_reference']
                assert observed['llm_calls']==1 and not observed['probability_estimated']
                assert observed['approvals_granted']==0
            params={'dataset':'demo','training':[{'contacts':0,'spend_minor':0,'observed_clients':0} for _ in range(8)],
                    'queries':[{'contacts':0,'spend_minor':0}]}
            checked=e.execute({'service':'interpret','operation':'prediction.explain',
                               'key':'explain-constant-data','params':params},True)
            assert checked['state']=='succeeded',checked
            explained=checked['result']['result']
            assert explained['additive_reconstruction_verified']
            assert explained['mean_absolute_contribution']=={'contacts':0.0,'spend_minor':0.0}
            assert not explained['quality_calibrated']
            for symbols in ([0,0],[15,14,13,12,11,10]):
                checked=e.execute({'service':'transformerlens','operation':'activations.check',
                    'key':'activation-observe-'+str(len(symbols)), 'params':{'dataset':'demo',
                    'symbol_ids':symbols,'intervention':'observe'}},True)
                assert checked['state']=='succeeded',checked
                activation=checked['result']['result']
                assert activation['max_output_change']==0 and activation['max_restored_output_error']==0
                assert activation['hooks_remaining']==0 and activation['max_future_attention']==0
            for label,values in [('zero',[0]*64),('one',[17]),('partial',[17]*65),('extreme',[-1000,1000]*256)]:
                checked=e.execute({'service':'bitsandbytes','operation':'quantization.check',
                    'key':'quantization-'+label,'params':{'dataset':'demo','values':values}},True)
                assert checked['state']=='succeeded',checked
                q=checked['result']['result']
                assert q['native_cpu_path_used'] and q['scalar_reconstruction_max_error']<1e-4
                if label!='extreme':assert q['max_absolute_reconstruction_error']==0
            cases=[{'decision':'review','approved':False,'item_count':0,'variant':variant}
                   for variant in ('canonical','truncated','extra_field','string_count')]
            cases += [{'decision':'defer','approved':False,'item_count':n,'variant':'canonical'} for n in (0,3,4,6)]
            checked=e.execute({'service':'guidance','operation':'schema.check','key':'schema-all-boundaries',
                'params':{'dataset':'demo','cases':cases}},True)
            assert checked['state']=='succeeded',checked
            shape=checked['result']['result']
            assert shape['accepted_indices']==[0,4,5] and shape['parser_threads_remaining']==0
            for decision in ('review','defer','execute'):
                for mode in ('dry_run','send'):
                    prefix_cases=[{'decision':decision,'mode':mode,'cut':cut} for cut in ('complete','value_prefix','object_prefix','bad_suffix')]
                    checked=e.execute({'service':'lm-format-enforcer','operation':'prefix.check',
                        'key':'prefix-'+decision+'-'+mode,'params':{'dataset':'demo','cases':prefix_cases}},True)
                    assert checked['state']=='succeeded',checked
                    prefix=checked['result']['result']
                    assert prefix['complete_count']==(1 if decision!='execute' and mode=='dry_run' else 0)
                    assert prefix['viable_count']==(3 if decision!='execute' and mode=='dry_run' else 1)
            for case, count in (('plane',5),('line',8)):
                checked=e.execute({'service':'usearch','operation':'neighbors.check','key':'neighbors-'+case,
                    'params':{'dataset':'demo','case':case}},True)
                assert checked['state']=='succeeded',checked
                neighbors=checked['result']['result']
                assert neighbors['vectors_indexed']==count and neighbors['graph_entries_reachable']==count
                assert neighbors['independent_scalar_reference_verified']
                assert neighbors['scan_distance_max_error']<1e-4 and neighbors['walk_distance_max_error']<1e-4
            for mode, values, expected in [('score',[-2,5,5,None],[1,2,0,None]), ('rank',[3,2,1,None],[2,1,0,None]), ('score',[None,None],[0,1]), ('rank',[None,None],[0,1])]:
                checked=e.execute({'service':'rerankers','operation':'results.rank','key':'rank-'+mode+'-'+str(len(values)),
                    'params':{'dataset':'demo','mode':mode,'values':values,'limit':len(values)}},True)
                assert checked['state']=='succeeded',checked
                ranked=checked['result']['result']
                wanted=[i if i is not None else 3 for i in expected]
                assert ranked['selected_indices']==wanted and ranked['independent_numeric_order_verified']
            for i,coefficients in enumerate([[0,0],[7],[0,1,0,-1],[-2,0,2],[1,0,0,0,0,1]]):
                checked=e.execute({'service':'sympy','operation':'polynomial.check','key':'polynomial-'+str(i),
                    'params':{'dataset':'demo','coefficients':coefficients,'points':[-2,0,1,3]}},True)
                assert checked['state']=='succeeded',checked
                checked=checked['result']['result']
                assert checked['independent_evaluation_verified'] and checked['independent_factor_product_verified']
                if coefficients==[0,0]: assert checked['degree'] is None and checked['evaluations']==[0]*4
            for i,edges,start,wanted in [(0,[],3,[3]), (1,[[0,1],[0,2],[1,3],[2,3]],0,[0,1,2,3])]:
                checked=e.execute({'service':'rdflib','operation':'reachability.check','key':'closure-'+str(i),
                    'params':{'dataset':'demo','node_count':4,'edges':edges,'start':start}},True)
                assert checked['state']=='succeeded',checked
                assert checked['result']['result']['reachable_indices']==wanted
                assert checked['result']['result']['independent_closure_verified']
            for i,budget,units,yield_,expected,count in [(0,0,3,6,'unsat',0),(1,45,9,0,'sat',64),
                                                       (2,45,9,33,'sat',1),(3,0,0,0,'sat',1)]:
                checked=e.execute({'service':'z3','operation':'constraints.check','key':'native-constraints-'+str(i),
                    'params':{'dataset':'demo','spend_limit':budget,'unit_limit':units,'minimum_yield':yield_}},True)
                assert checked['state']=='succeeded',checked
                native=checked['result']['result']
                assert native['verdict']==expected and native['feasible_assignments']==count
                assert native['finite_reference_verified'] and not native['real_world_claim_verified']
    assert not calls
    return {'schema':'verdugo.executive666.acceptance.v1','services':list(services),
            'original_sdks_executed':True,'mocked_sdks':False,'dataset':'demo',
            'joint_workflow':result,'budget_rejection':data,'negative_process_cases':negative_process_cases,
            'approval_gate_verified':True,'sqlite_restart_replay_verified':True,
            'cli_mcp_shared_engine_verified':True,'live_verified':False,
            'models_used':3,'language_models_used':1,'ephemeral_additive_models_used':1,'untrained_toy_transformers_used':1,'selected_model_controls_passed':True,'model_accuracy_calibrated':False,'external_effects':0,'batch_1_complete':False,
            'os_network_namespace':os.getenv('VERDUGO_OS_NETWORK_ISOLATED')=='1'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    evidence=accept();Path(args.out).write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({k:v for k,v in evidence.items() if k not in ('joint_workflow','budget_rejection')}))
