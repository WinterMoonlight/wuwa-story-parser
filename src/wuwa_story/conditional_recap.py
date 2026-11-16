"""Bounded choice projection of an explicitly anchored conditional recap.

This selects a configuration reading scenario, not a game runtime route.
"""
from copy import deepcopy
from .branch_recap import annotate_branch_entries
from .variables import VariableEnvironment, set_var_shape, compare_var_shape
from .export_task import Exporter, walk, flow_key
from .rendering import render_result


def project_conditional_recap(backbone, nodes, source, choices=None):
    entries = backbone['order_source']['entries']
    annotations = annotate_branch_entries(entries, nodes)
    proofs = []
    by_index = {s['entry_index']: s for s in backbone['segments']}
    for sid in sorted({a['selector_id'] for a in annotations.values()}):
        tagged = {i: a for i, a in annotations.items() if a['selector_id'] == sid}
        indices = sorted(tagged)
        if indices != list(range(indices[0], indices[-1]+1)):
            continue
        writer = by_index.get(indices[0]-1)
        if not writer or not writer.get('source_actions'):
            continue
        selectors = [n for n in nodes if n.get('Id') == sid]
        if len(selectors) != 1:
            continue
        selector = selectors[0]
        if not isinstance(selector.get('Slots'), list) or len(selector['Slots']) != 2:
            continue
        conditions = []
        for slot in selector.get('Slots', []):
            c = slot.get('Condition', {})
            if (not isinstance(c, dict) or set(c) != {'Type', 'Conditions'}
                    or type(c['Type']) is not int or c['Type'] != 0
                    or not isinstance(c['Conditions'], list) or len(c['Conditions']) != 1):
                break
            c = c['Conditions'][0]
            if not compare_var_shape(c) or c['Var1']['Source'] != 'Self':
                break
            conditions.append(c)
        if len(conditions) != 2 or {c['Var2']['Value'] for c in conditions} != {False, True}:
            continue
        ref = conditions[0]['Var1']
        if any(c['Var1'] != ref for c in conditions):
            continue
        owners = [n for n in nodes if n.get('Condition', {}).get('Type') == 'PlayFlow'
                  and n['Condition'].get('Flow', {}).get('FlowListName')
                  and flow_key(n['Condition']['Flow']) == writer['state_key']]
        if len(owners) != 1 or owners[0].get('ParentNodeId') != selector.get('ParentNodeId'):
            continue
        if not any(n.get('Id') == selector.get('ParentNodeId') and n.get('Type') == 'Sequence' for n in nodes):
            continue
        # Explicit unique tip immediately precedes the writer in the recap.
        wi = writer['entry_index']
        tip = entries[wi-1].get('TidTip') if wi else None
        if not tip or tip != owners[0].get('TidTip') or sum(n.get('TidTip') == tip for n in nodes) != 1:
            continue
        action_tree = writer['source_actions']
        option_items = [o for o in walk(action_tree) if o.get('Options') and any(
            a.get('Name') == 'SetVar' for option in o['Options'] for a in option.get('Actions', []))]
        if len(option_items) != 1 or len(option_items[0]['Options']) != 2:
            continue
        options = option_items[0]['Options']
        assignments = [o for o in walk(action_tree) if o.get('Name') == 'SetVar']
        if len(assignments) != 2 or any(len(o.get('Actions', [])) != 1 for o in options):
            continue
        if any(not set_var_shape(a) or a['Params']['VarLeft'] != ref for a in assignments):
            continue
        if any(o['Actions'][0] not in assignments for o in options):
            continue
        env = VariableEnvironment(f"quest:{backbone['quest_id']}:selector:{sid}")
        parser = Exporter(choices=choices, source=source, allow_incomplete=True, variable_environment=env)
        parser.state_key = writer['state_key']
        try:
            if parser.actions(action_tree):
                continue
            values = [env.evaluate(c) for c in conditions]
            if values.count(True) != 1 or any(v is None for v in values):
                continue
        except (ValueError, KeyError, TypeError, IndexError):
            continue
        chosen = values.index(True)
        rendered = render_result({'title': '', 'route': {'choices': parser.decisions}, 'events': parser.events})
        writer.update(status='parsed', events=rendered['events'], route=rendered['route'],
                      action_trace=parser.action_log, talk_groups=parser.talk_coverage,
                      unverified_content=parser.unverified_content,
                      missing_text_ids=sorted(set(parser.missing)), variable_trace=env.trace)
        writer.pop('error', None)
        excluded = []
        for i, a in tagged.items():
            segment = by_index.get(i)
            if segment is None:
                continue
            if a['slot_index'] != chosen:
                segment['unselected_original'] = deepcopy(segment)
                segment.update(status='excluded_branch', events=[], branch_selection=a)
                excluded.append(i)
            else:
                segment['branch_selection'] = a
        proofs.append({'selector_id': sid, 'writer_entry_index': wi,
                       'writer_node_id': owners[0]['Id'], 'selected_slot': chosen,
                       'condition_results': values, 'conditions': conditions,
                       'variable_snapshot': env.snapshot(), 'annotations': tagged,
                       'excluded_entry_indices': excluded,
                       'runtime_route_verified': False,
                       'assumption': 'Selected option value remains unchanged until this selector; recap configuration scenario only'})
    if proofs:
        backbone['conditional_selections'] = proofs
        backbone['parsed_segments'] = sum(s['status'] == 'parsed' for s in backbone['segments'])
        backbone['blocked_segments'] = sum(s['status'] == 'blocked' for s in backbone['segments'])
        backbone['excluded_segments'] = sum(s['status'] == 'excluded_branch' for s in backbone['segments'])
    return proofs
