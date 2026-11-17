"""Insert omitted finish flows at exact and otherwise-empty recap tip anchors."""
import math
from .export_task import flow_key, walk
from .task_flows import classify_task_flows
from .dependency_positions import _sync_flow
from .levelplay_completion import ancestry


def anchored_finish_flows(quest, nodes, entries, *, allow_nested=False):
    roots = [n for n in nodes if n.get('ParentNodeId') == 0]
    if len(roots) != 1 or roots[0]['Type'] != 'Sequence':
        return [], []
    root = roots[0]
    if any(k in root for k in ('Condition', 'ExitCondition', 'FailedCondition', 'Slots')):
        return [], []
    if not allow_nested and any(n.get('ParentNodeId') != root['Id'] or n['Type'] not in {'ChildQuest', 'QuestSucceed'} for n in nodes if n is not root):
        return [], []
    if allow_nested and any(ancestry(n['Id'], nodes)[1] for n in nodes):
        return [], []
    occurrences = classify_task_flows(quest, nodes)
    existing = {flow_key(e['Flow']) for e in entries if e.get('Flow', {}).get('FlowListName')}
    inserts, proofs = {}, []
    for node in nodes:
        if node['Type'] != 'ChildQuest' or set(node.get('Condition', {})) != {'Type', 'Pos', 'Range'} or node['Condition']['Type'] != 'ReachArea':
            continue
        if any(k in node for k in ('ExitCondition', 'FailedCondition', 'Slots')):
            continue
        if allow_nested:
            condition = node['Condition']
            position = condition['Pos']
            if (not isinstance(position, dict) or set(position) != {'X', 'Y', 'Z'}
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in position.values())
                    or type(condition['Range']) not in (int, float)
                    or not math.isfinite(condition['Range']) or condition['Range'] <= 0):
                continue
        chain, error = ancestry(node['Id'], nodes)
        if allow_nested and (error or not chain or chain[-1]['Id'] != root['Id']
                or any(n.get('Type') != 'Sequence' or any(n.get(k) for k in ('Condition', 'ExitCondition', 'FailedCondition', 'Slots'))
                       for n in chain[1:])):
            continue
        actions = node.get('FinishActions', [])
        calls = [(i, a) for i, a in enumerate(actions) if a.get('Name') == 'PlayFlow']
        if len(calls) != 1:
            continue
        index, action = calls[0]
        if allow_nested and (index != 0 or _sync_flow(action) is None):
            continue
        params = action.get('Params', {})
        if set(params) != {'FlowListName', 'FlowId', 'StateId'} or not params['FlowListName']:
            continue
        key = flow_key(params)
        if key in existing or len(occurrences.get(key, [])) != 1:
            continue
        if action.get('Async') or any(a.get('Async') or a.get('Params', {}).get('Async') for a in actions[:index]):
            continue
        if len([o for o in walk(node) if o.get('FlowListName') and 'StateId' in o]) != 1:
            continue
        tip = node.get('TidTip')
        anchors = [i for i, e in enumerate(entries) if tip and e.get('TidTip') == tip]
        if len(anchors) != 1 or sum(n.get('TidTip') == tip for n in nodes) != 1:
            continue
        anchor = anchors[0]
        end = next((i for i in range(anchor+1, len(entries)) if entries[i].get('TidTip')), len(entries))
        if any(e.get('Flow', {}).get('FlowListName') for e in entries[anchor:end]):
            continue
        inserts[anchor] = key
        proof = {'state_key': key, 'node_id': node['Id'], 'tip_id': tip,
                       'recap_entry_index': anchor, 'finish_action_index': index,
                       'condition': node['Condition'], 'source_action': action,
                       'requirement_scope': 'Invoked on completion of this ReachArea step in a flat Sequence',
                       'ordering_basis': 'unique exact tip anchor with empty flow block', 'runtime_verified': False}
        if allow_nested:
            proof.update(ancestor_ids=[n['Id'] for n in chain[1:]], recap_block_end_index=end,
                         source_finish_actions=actions,
                         requirement_scope='First synchronous finish call of this ReachArea step under unconditional Sequence ancestors')
        proofs.append(proof)
    ordered = []
    for i, entry in enumerate(entries):
        if entry.get('Flow', {}).get('FlowListName'):
            ordered.append(flow_key(entry['Flow']))
        if i in inserts:
            ordered.append(inserts[i])
    return ordered, proofs
