"""Insert omitted finish flows at exact and otherwise-empty recap tip anchors."""
from .export_task import flow_key, walk
from .task_flows import classify_task_flows


def anchored_finish_flows(quest, nodes, entries):
    roots = [n for n in nodes if n.get('ParentNodeId') == 0]
    if len(roots) != 1 or roots[0]['Type'] != 'Sequence':
        return [], []
    root = roots[0]
    if any(k in root for k in ('Condition', 'ExitCondition', 'FailedCondition', 'Slots')):
        return [], []
    if any(n.get('ParentNodeId') != root['Id'] or n['Type'] not in {'ChildQuest', 'QuestSucceed'} for n in nodes if n is not root):
        return [], []
    occurrences = classify_task_flows(quest, nodes)
    existing = {flow_key(e['Flow']) for e in entries if e.get('Flow', {}).get('FlowListName')}
    inserts, proofs = {}, []
    for node in nodes:
        if node['Type'] != 'ChildQuest' or set(node.get('Condition', {})) != {'Type', 'Pos', 'Range'} or node['Condition']['Type'] != 'ReachArea':
            continue
        if any(k in node for k in ('ExitCondition', 'FailedCondition', 'Slots')):
            continue
        actions = node.get('FinishActions', [])
        calls = [(i, a) for i, a in enumerate(actions) if a.get('Name') == 'PlayFlow']
        if len(calls) != 1:
            continue
        index, action = calls[0]
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
        proofs.append({'state_key': key, 'node_id': node['Id'], 'tip_id': tip,
                       'recap_entry_index': anchor, 'finish_action_index': index,
                       'condition': node['Condition'], 'source_action': action,
                       'requirement_scope': 'Invoked on completion of this ReachArea step in a flat Sequence',
                       'ordering_basis': 'unique exact tip anchor with empty flow block', 'runtime_verified': False})
    ordered = []
    for i, entry in enumerate(entries):
        if entry.get('Flow', {}).get('FlowListName'):
            ordered.append(flow_key(entry['Flow']))
        if i in inserts:
            ordered.append(inserts[i])
    return ordered, proofs
