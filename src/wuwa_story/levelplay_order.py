"""Adjacent synchronous gameplay calls form local fragments, never global anchors."""
import hashlib
from collections import Counter
from .export_task import Exporter, flow_actions, flow_key
from .rendering import render_result


def sync_flow(action):
    if not isinstance(action, dict):
        return False
    params = action.get('Params', {})
    return (action.get('Name') == 'PlayFlow' and action.get('Async', False) is False
            and set(action) <= {'Name','Params','Async','ActionId','ActionGuid'}
            and isinstance(params, dict) and set(params) == {'FlowListName','FlowId','StateId'}
            and isinstance(params['FlowListName'], str) and bool(params['FlowListName'])
            and type(params['FlowId']) is int and type(params['StateId']) is int)


def local_sequences(audits, links, states, source, candidate_keys, choices=None):
    reviews = []
    counts = Counter((l['levelplay_id'], l['state_key']) for l in links)
    for audit in audits:
        play_id = audit['levelplay_id']
        for node in audit['nodes']:
            for phase in ('Actions','EnterActions','FinishActions'):
                actions = node.get(phase, [])
                i = 0
                while i < len(actions):
                    start = i
                    while i < len(actions) and sync_flow(actions[i]):
                        i += 1
                    run = actions[start:i]
                    if len(run) < 2:
                        i += 1
                        continue
                    keys = [flow_key(a['Params']) for a in run]
                    if not set(keys) & candidate_keys:
                        continue
                    review = {'levelplay_id':play_id,'node_id':node['Id'],'phase':phase,
                              'action_indices':list(range(start,i)), 'state_keys':keys,
                              'source_actions':run, 'relative_invocation_order_verified':True,
                              'scope':'same node activation and contiguous synchronous action list only',
                              'placement_verified':False,'runtime_verified':False,
                              'status':'blocked','segments':[],
                              'task_region_evidence':audit['task_conditions']}
                    reviews.append(review)
                    if any(counts[play_id,k] != 1 for k in keys) or len(set(keys)) != len(keys):
                        review['reason']='repeated_or_unresolved_call_occurrence'
                        continue
                    # Do not move or duplicate a flow already placed in the task body.
                    if not set(keys) <= candidate_keys:
                        review['reason']='not_all_calls_in_candidate_scope'
                        continue
                    try:
                        for key in keys:
                            blob = states[key]['BinData']
                            flow, fields = flow_actions(blob)
                            parser = Exporter(source=source, choices=choices, allow_incomplete=True)
                            parser.state_key = key
                            if parser.actions(flow):
                                raise ValueError('unexpected_control_outside_dialogue')
                            if any(e['kind']=='unparsed_content' for e in parser.events):
                                raise ValueError('unparsed_flow_content')
                            rendered = render_result({'title':'','events':parser.events,'route':{'choices':parser.decisions}})
                            review['segments'].append({'state_key':key,'events':rendered['events'],
                                'route':rendered['route'],'unverified_content':parser.unverified_content,
                                'source_actions':flow,'equivalent_action_fields':fields,
                                'sha256':hashlib.sha256(blob).hexdigest()})
                        review['status']='local_order_only'
                    except (ValueError, KeyError, TypeError, IndexError) as exc:
                        review['segments']=[]
                        review['reason']=str(exc)
    return reviews
