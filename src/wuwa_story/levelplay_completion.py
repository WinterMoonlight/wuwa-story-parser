"""Completion evidence is not a proof of a gameplay dialogue's recap position."""


def ancestry(node_id, nodes):
    by_id = {n['Id']: n for n in nodes}
    if len(by_id) != len(nodes):
        return [], 'duplicate_node_id'
    chain, seen = [], set()
    while node_id:
        if node_id in seen or node_id not in by_id:
            return chain, 'invalid_ancestry'
        seen.add(node_id)
        node = by_id[node_id]
        chain.append(node)
        node_id = node.get('ParentNodeId', 0)
    return chain, None


def completion_evidence(audit, node_id, task_nodes, entries):
    """Record exact gates and structural barriers without inventing sibling order."""
    play_id = audit['levelplay_id']
    chain, error = ancestry(node_id, audit['nodes'])
    result = {'levelplay_id': play_id, 'node_id': node_id,
              'placement_verified': False, 'mandatory_verified': False,
              'single_execution_verified': False, 'runtime_verified': False,
              'gameplay_ancestry': [{'node_id': n['Id'], 'type': n.get('Type')} for n in chain],
              'success_node_ids': [n['Id'] for n in audit['nodes'] if n.get('Type') == 'QuestSucceed'],
              'parallel_boundaries': [], 'recovery_nodes': [], 'task_gates': [],
              'reasons': ['no_explicit_completion_to_recap_edge']}
    if error:
        result['reasons'].append(error)
    for n in chain:
        if n.get('SaveConfig'):
            result['recovery_nodes'].append({'node_id': n['Id'], 'source': n['SaveConfig']})
        if n.get('Type') == 'ParallelSelect':
            children = [c for c in audit['nodes'] if c.get('ParentNodeId') == n['Id']]
            result['parallel_boundaries'].append({'node_id': n['Id'], 'count': n.get('Count'),
                'children': [{'node_id': c['Id'], 'type': c.get('Type'),
                              'failed_condition': c.get('FailedCondition')} for c in children]})
    if result['parallel_boundaries']:
        result['reasons'].append('parallel_outcome_not_simulated')
    if result['recovery_nodes']:
        result['reasons'].append('rollback_or_resume_not_simulated')
    for gate in audit['task_conditions']:
        node = gate['source_node']
        condition = node.get('Condition', {})
        task_chain, task_error = ancestry(node['Id'], task_nodes)
        item = {'node_id': node['Id'], 'condition': condition,
                'single_target_completion_gate': condition.get('Type') == 'CheckLevelPlay'
                    and condition.get('LevelPlayIds') == [play_id]
                    and type(condition.get('CompleteNumber')) is int and condition['CompleteNumber'] == 1,
                'lifecycle_calls': [], 'ancestor_tip_matches': [],
                'task_ancestry': [{'node_id': n['Id'], 'type': n.get('Type')} for n in task_chain],
                'ancestry_error': task_error}
        for phase in ('EnterActions', 'FinishActions'):
            for i, action in enumerate(node.get(phase, [])):
                if action.get('Name') != 'EnableLevelPlay':
                    continue
                configs = action.get('Params', {}).get('Configs', [])
                if any(c.get('LevelPlayId') == play_id for c in configs):
                    item['lifecycle_calls'].append({'phase': phase, 'index': i, 'source_action': action})
        for ancestor in task_chain:
            tip = ancestor.get('TidTip')
            positions = [i for i, e in enumerate(entries) if tip and e.get('TidTip') == tip]
            if positions:
                item['ancestor_tip_matches'].append({'node_id': ancestor['Id'], 'tid_tip': tip,
                    'entry_indices': positions, 'scope': 'region_only_not_dialogue_position'})
        result['task_gates'].append(item)
    if not result['task_gates']:
        result['reasons'].append('no_task_completion_gate')
    elif not any(g['ancestor_tip_matches'] for g in result['task_gates']):
        result['reasons'].append('no_task_or_ancestor_tip_in_recap')
    result['reasons'].append('parent_link_does_not_define_sibling_execution_order')
    return result
