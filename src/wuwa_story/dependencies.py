"""Call-site dependencies and conservative parallel proximity supplements."""
from .export_task import flow_key
from .task_flows import classify_task_flows
from .external import node_context


def dependency_report(quest, nodes, ordered):
    occurrences = classify_task_flows(quest, nodes)
    edges, parallels, supplements = [], [], []
    for node in nodes:
        condition = node.get('Condition', {})
        if condition.get('Type') == 'PlayFlow' and condition.get('Flow', {}).get('FlowListName'):
            for i, action in enumerate(node.get('FinishActions', [])):
                if action.get('Name') == 'PlayFlow':
                    edges.append({'from_state': flow_key(condition['Flow']), 'from_event': 'condition_flow_completed',
                                  'to_state': flow_key(action['Params']), 'to_event': 'finish_action_invoked',
                                  'node_id': node['Id'], 'finish_action_index': i,
                                  'scope': 'same node activation', 'runtime_executed': False})
    children = {}
    for n in nodes:
        children.setdefault(n.get('ParentNodeId'), []).append(n)
    def finish_flow(n):
        calls = [(i, a) for i, a in enumerate(n.get('FinishActions', [])) if a.get('Name') == 'PlayFlow']
        return calls[0] if len(calls) == 1 else None
    def comparable(c):
        return {k: v for k, v in c.items() if k != 'Range'}
    for group in nodes:
        if group['Type'] != 'ParallelSelect' or group.get('Count') != 1:
            continue
        members = children.get(group['Id'], [])
        if len(members) != 2:
            continue
        direct = [n for n in members if n['Type'] == 'ChildQuest']
        wrappers = [n for n in members if n['Type'] == 'AlwaysFalse']
        if len(direct) != 1 or len(wrappers) != 1:
            continue
        indirect = children.get(wrappers[0]['Id'], [])
        if len(indirect) != 1 or indirect[0]['Type'] != 'ChildQuest':
            continue
        inner, outer = direct[0], indirect[0]
        ci, co = inner.get('Condition', {}), outer.get('Condition', {})
        if ci.get('Type') != 'ReachArea' or comparable(ci) != comparable(co):
            continue
        if type(ci.get('Range')) not in (int, float) or type(co.get('Range')) not in (int, float) or not 0 < ci['Range'] < co['Range']:
            continue
        fi, fo = finish_flow(inner), finish_flow(outer)
        if not fi or not fo or fo[1].get('Async') is not True or fi[1].get('Async'):
            continue
        ki, ko = flow_key(fi[1]['Params']), flow_key(fo[1]['Params'])
        if ki not in ordered or ko in ordered or len(occurrences.get(ko, [])) != 1:
            continue
        if outer.get('EnterActions') or len(outer.get('FinishActions', [])) != 1:
            continue
        context = node_context(outer, nodes)
        if context['route_scope'] == 'failure_branch':
            continue
        evidence = {'group_id': group['Id'], 'count': 1, 'wrapper_type': 'AlwaysFalse',
                    'inner_node_id': inner['Id'], 'outer_node_id': outer['Id'],
                    'inner_state': ki, 'outer_state': ko, 'inner_condition': ci, 'outer_condition': co,
                    'outer_source_action': fo[1], 'context': context,
                    'ordering': 'no proven sibling playback order', 'mandatory': 'unverified',
                    'wrapper_runtime_semantics': 'not simulated; not treated as unreachable',
                    'reason': 'Concentric ranges are spatial evidence, not a completion-before relation'}
        parallels.append(evidence)
        supplements.append(ko)
    positions = {key: i for i, key in enumerate(ordered)}
    conflicts = [e for e in edges if e['from_state'] in positions and e['to_state'] in positions
                 and positions[e['from_state']] > positions[e['to_state']]]
    return {'edges': edges, 'recap_dependency_conflicts': conflicts,
            'parallel_relations': parallels, 'separate_state_keys': supplements,
            'scope': 'Explicit same-node completion dependencies and inspected parallel range pattern only',
            'global_order_verified': False}


def read_supplement(key, read_rows):
    import hashlib
    from types import SimpleNamespace
    from .export_task import Exporter, flow_actions
    from .rendering import render_text
    matches = [r for r in read_rows('db_flowState.db', 'flowstate') if r['StateKey'] == key]
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous parallel flow')
    parser = Exporter(source=SimpleNamespace(rows=read_rows), allow_incomplete=True)
    parser.state_key = key
    actions, fields = flow_actions(matches[0]['BinData'])
    if parser.actions(actions):
        raise ValueError('Unexpected parallel flow control')
    return {'state_key': key, 'route_choices': parser.decisions, 'action_trace': parser.action_log, 'talk_groups': parser.talk_coverage, 'source_actions': actions, 'action_fields': fields,
            'sha256': hashlib.sha256(matches[0]['BinData']).hexdigest(),
            'unverified_content': parser.unverified_content, 'missing_text_ids': parser.missing,
            'texts': [{'text_id': e.get('text_id'), 'raw_text': e['raw_text'],
                       'display_name': render_text(e.get('display_name', '旁白')), 'source_event': e,
                       'missing': e.get('text_id') in parser.missing} for e in parser.events]}
