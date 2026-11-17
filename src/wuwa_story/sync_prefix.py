"""Place dialogue prefixes using unique synchronous task calls."""
from copy import deepcopy
import struct
from .export_task import Exporter, flow_actions, flow_key, walk
from .rendering import render_result


def insert_sync_dialogue_prefix(review, quest, nodes, backbone, states, source, choices=None):
    """Place a complete first call immediately before its unique recap anchor."""
    from .dependency_positions import _sync_flow
    from .levelplay_completion import ancestry
    from .task_flows import classify_task_flows
    from .task_local_order import _flow_segment

    key = review['state_key']
    if review.get('placement_verified') or len(review['owner_nodes']) != 1 or key not in states:
        return
    node = review['owner_nodes'][0]
    phases = {'Action': 'Actions', 'ChildQuest': 'FinishActions'}
    phase = phases.get(node.get('Type'))
    if phase is None or any(node.get(k) for k in ('ExitCondition', 'FailedCondition', 'Slots')):
        return
    if phase == 'Actions' and node.get('Condition'):
        return
    if len({n['Id'] for n in nodes}) != len(nodes):
        return
    chain, error = ancestry(node['Id'], nodes)
    if (error or len(chain) < 2 or any(n.get('Type') != 'Sequence' for n in chain[1:])
            or any(n.get(k) for n in chain[1:] for k in ('Condition', 'ExitCondition', 'FailedCondition', 'Slots'))):
        return
    actions = node.get(phase, [])
    if not isinstance(actions, list) or len(actions) < 2 or _sync_flow(actions[0]) != key:
        return
    anchor = _sync_flow(actions[1])
    if anchor is None or anchor == key:
        return
    occurrences = classify_task_flows(quest, nodes)
    if any(len(occurrences.get(k, [])) != 1 for k in (key, anchor)):
        return
    targets = [s for s in backbone['segments'] if s['state_key'] == anchor]
    used = {s['state_key'] for s in backbone['segments']}
    used.update(f['state_key'] for s in backbone['segments'] for f in s.get('inserted_task_flows', []))
    if (key in used or len(targets) != 1 or targets[0]['status'] != 'parsed'
            or targets[0].get('prefix_event_count') or targets[0].get('inserted_task_flows')):
        return
    try:
        parsed = _flow_segment(key, states, source, choices)
    except struct.error:
        return
    if (parsed is None or not parsed['events'] or parsed['missing_text_ids'] or parsed['unverified_content']
            or any(e['kind'] not in {'dialogue', 'choice', 'narration', 'center_text'} for e in parsed['events'])):
        return
    proof = {'kind': 'task_sync_prefix', 'node_id': node['Id'], 'phase': phase,
             'action_indices': [0, 1], 'state_key': key, 'before_state': anchor,
             'source_actions': deepcopy(actions[:2]), 'ancestor_ids': [n['Id'] for n in chain[1:]],
             'basis': 'first two adjacent synchronous calls; unique task occurrences and recap anchor',
             'relative_order_verified': True, 'runtime_verified': False}
    events = deepcopy(parsed['events'])
    for event in events:
        event['task_placement'] = deepcopy(proof)
    targets[0]['events'][0:0] = events
    targets[0].setdefault('inserted_task_flows', []).append({
        'state_key': key, 'proof': proof, 'source_actions': parsed['source_actions'],
        'action_fields': parsed['action_fields'], 'sha256': parsed['sha256'], 'route': parsed['route']})
    review.update(classification='placed_sync_dialogue_prefix', placement_verified=True,
                  proof=proof, text_evidence=events, visible_event_count=len(events), complete=True)


def bridge_action(action):
    if action.get('Async', False) is not False or set(action) - {'Name', 'Params', 'Async', 'ActionId', 'ActionGuid'}:
        return False
    p = action.get('Params', {})
    if action.get('Name') == 'AwakeEntity':
        return set(p) == {'EntityIds'} and bool(p['EntityIds']) and all(type(i) is int for i in p['EntityIds'])
    if action.get('Name') == 'UnlockSystemItem':
        s = p.get('SystemOption', {}); u = s.get('UnlockOption', {})
        return (set(p) == {'SystemOption'} and set(s) == {'Type', 'UnlockOption'} and s['Type'] == 'AtlasSystem'
                and set(u) == {'Type', 'Id'} and u['Type'] == 'PlotPhoto' and type(u['Id']) is int)
    return False


def insert_qte_prefix(review, quest, nodes, backbone, states, source):
    owners = review['owner_nodes']; key = review['state_key']
    if len(owners) != 1 or key not in states:
        return
    node = owners[0]; chain = review['ancestor_chains'][0]['ancestors']
    if (node.get('Type') != 'ChildQuest' or not chain or any(a['type'] != 'Sequence' for a in chain)
            or node.get('FailedCondition') or node.get('ExitCondition')):
        return
    actions = node.get('FinishActions', [])
    def call(a):
        return (a.get('Name') == 'PlayFlow' and a.get('Async', False) is False
                and set(a.get('Params', {})) == {'FlowListName', 'FlowId', 'StateId'}
                and not set(a) - {'Name', 'Params', 'Async', 'ActionId', 'ActionGuid'})
    starts = [i for i, a in enumerate(actions) if call(a) and flow_key(a['Params']) == key]
    if len(starts) != 1:
        return
    start = starts[0]; end = start + 1
    while end < len(actions) and bridge_action(actions[end]):
        end += 1
    if end == len(actions) or not call(actions[end]):
        return
    anchor = flow_key(actions[end]['Params'])
    occurrences = lambda k: sum(1 for o in walk([quest, nodes]) if o.get('FlowListName')
        and 'FlowId' in o and 'StateId' in o and flow_key(o) == k)
    targets = [s for s in backbone['segments'] if s['state_key'] == anchor]
    if len(targets) != 1 or targets[0]['status'] != 'parsed' or occurrences(key) != 1 or occurrences(anchor) != 1:
        return
    try:
        raw, fields = flow_actions(states[key]['BinData'])
    except (ValueError, KeyError, TypeError, IndexError, struct.error):
        return
    # Limit to a single terminal ShowTalk with an explicit, exhaustive linear sequence.
    if not raw or raw[-1].get('Name') != 'ShowTalk' or any(a.get('Name') not in {'SetPlotMode', 'HideByRangeInFlow'} for a in raw[:-1]):
        return
    p = raw[-1]['Params']; items = p.get('TalkItems', []); seq = p.get('TalkSequence')
    if not items or seq != [[i.get('Id') for i in items]] or len({i.get('Id') for i in items}) != len(items):
        return
    stop = next((i for i, item in enumerate(items) if item.get('Type') == 'QTE'), None)
    if not stop or any(i.get('Type') != 'QTE' for i in items[stop:]):
        return
    if any(i.get('Type') != 'Talk' or i.get('Actions') or i.get('Options') or i.get('Condition') for i in items[:stop]):
        return
    prefix = deepcopy(raw)
    prefix[-1]['Params']['TalkItems'] = items[:stop]
    prefix[-1]['Params']['TalkSequence'] = [seq[0][:stop]]
    parser = Exporter(source=source, allow_incomplete=True); parser.state_key = key
    try:
        control = parser.actions(prefix)
    except (ValueError, KeyError, TypeError, IndexError):
        return
    if control or parser.missing or parser.unverified_content or parser.decisions:
        return
    events = render_result({'title': '', 'route': {'choices': []}, 'events': parser.events})['events']
    from .qte_evidence import inspect_qte
    from .database import texts
    qte_evidence = inspect_qte(p, texts)
    proof = {'node_id': node['Id'], 'before_state': anchor, 'source_actions': actions[start:end+1],
             'basis': 'synchronous calls with bounded bridge actions; explicit dialogue prefix before QTE',
             'runtime_verified': False, 'qte_outcomes_verified': False}
    for e in events:
        e['task_placement'] = proof
    events.append({'kind': 'recap_gap', 'state_key': key, 'display_name': '缺口',
                   'text': '【此处的快速反应操作及其结果尚未还原，后续正文继续】', 'task_placement': proof})
    targets[0]['events'][0:0] = events
    targets[0].setdefault('inserted_task_flows', []).append({'state_key': key, 'proof': proof,
        'source_actions': raw, 'action_fields': fields, 'unparsed_items': items[stop:]})
    review.update(classification='placed_dialogue_prefix', placement_verified=True, proof=proof,
                  text_evidence=events, visible_event_count=len(events)-1, complete=False,
                  unparsed_qte_count=len(items)-stop, qte_evidence=qte_evidence)
