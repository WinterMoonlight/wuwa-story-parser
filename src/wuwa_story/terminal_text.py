"""Prove an explicit local text end while retaining unexecuted state controls."""
from copy import deepcopy

from .combined_information import jump_target
from .variables import set_var_shape


def synchronous(action, name):
    return (isinstance(action, dict) and action.get('Name') == name
            and action.get('Async', False) is False
            and set(action) <= {'Name', 'Params', 'Async', 'ActionId', 'ActionGuid'})


def terminal_actions(actions):
    if not isinstance(actions, list) or len(actions) != 3:
        return False
    write, finish_state, finish_talk = actions
    return (set_var_shape(write) and write['Params']['VarLeft']['Source'] == 'Self'
            and synchronous(finish_state, 'FinishState') and finish_state.get('Params') == {}
            and synchronous(finish_talk, 'FinishTalk') and finish_talk.get('Params') == {})


def project_terminal_text(actions):
    """Only accept a terminal ShowTalk whose complete sequence graph agrees."""
    if not actions or not synchronous(actions[-1], 'ShowTalk'):
        return None
    from .export_task import walk
    if sum(obj.get('Name') == 'ShowTalk' for obj in walk(actions)) != 1:
        return None
    params = actions[-1].get('Params', {})
    if not isinstance(params, dict):
        return None
    items = params.get('TalkItems')
    groups = params.get('TalkSequence')
    transitions = params.get('SequenceTransitions')
    names = params.get('SequenceNames')
    if (not isinstance(items, list) or not items or not all(isinstance(item, dict) for item in items)
            or not isinstance(groups, list) or not groups
            or not all(isinstance(group, list) and group for group in groups)
            or not isinstance(transitions, dict) or not isinstance(names, list)
            or len(names) != len(groups)):
        return None
    ids = [item.get('Id') for item in items]
    flat = [item_id for group in groups for item_id in group]
    if not all(type(value) is int for value in flat):
        return None
    if not all(type(value) is int for value in ids) or len(set(ids)) != len(ids) or flat != ids:
        return None
    if set(transitions) != {str(index) for index in range(len(groups))}:
        return None
    if any(any('condition' in key.lower() for key in obj) for obj in walk(items)):
        return None
    by_id = {item['Id']: item for item in items}
    group_starts = {group[0]: index for index, group in enumerate(groups)}
    terminals = []
    for index, group in enumerate(groups):
        expected = []
        for item_id in group:
            item = by_id[item_id]
            if item.get('Type') != 'Talk':
                return None
            ops, options = item.get('Actions', []), item.get('Options', [])
            if item_id != group[-1]:
                if ops or options:
                    return None
                continue
            if terminal_actions(ops) and not options:
                terminals.append({'talk_id': item_id, 'source_actions': deepcopy(ops)})
                expected = [(-1, '')]
            elif options and not ops:
                for option in options:
                    if (not isinstance(option, dict) or set(option) - {'TextId','PlotLineId','PlotLineKey','TidTalkOption','Actions','Icon'}):
                        return None
                    target = jump_target(option.get('Actions'))
                    if target not in group_starts or group_starts[target] <= index:
                        return None
                    expected.append((group_starts[target], option.get('TidTalkOption')))
            elif not options:
                target = jump_target(ops)
                if target not in group_starts or group_starts[target] <= index:
                    return None
                expected = [(group_starts[target], '')]
            else:
                return None
        edges = transitions[str(index)]
        if not isinstance(edges, list) or not edges:
            return None
        actual = []
        for edge in edges:
            if (not isinstance(edge, dict) or set(edge) != {'NextSequenceIndex', 'OptionText', 'OptionTextKey'}
                    or type(edge['NextSequenceIndex']) is not int or not isinstance(edge['OptionText'], str)):
                return None
            value = (edge['NextSequenceIndex'], edge['OptionTextKey'])
            if value not in actual:
                actual.append(value)
        if actual != expected:
            return None
    if not terminals:
        return None
    projected = deepcopy(actions)
    terminal_ids = {terminal['talk_id'] for terminal in terminals}
    for item in projected[-1]['Params']['TalkItems']:
        if item['Id'] in terminal_ids:
            item['Actions'] = item['Actions'][-1:]
    evidence = {'kind': 'terminal_text_projection', 'terminal_controls': terminals,
                'selected_text_complete': True, 'runtime_completion_verified': False,
                'state_controls_executed': False, 'cross_segment_propagation': False,
                'basis': 'final ShowTalk, matching acyclic sequence graph and explicit FinishTalk'}
    return projected, evidence


def last_item_terminal_evidence(actions, boundary, reached_talk_id):
    """The final reached item can exhaust text without defining FinishState."""
    if boundary.source_action.get('Name') != 'FinishState' or not actions or not synchronous(actions[-1], 'ShowTalk'):
        return None
    from .export_task import walk
    if sum(obj.get('Name') == 'ShowTalk' for obj in walk(actions)) != 1:
        return None
    params = actions[-1].get('Params', {})
    items = params.get('TalkItems', [])
    if not items or params.get('TalkSequence') is not None:
        return None
    if any(item.get('Type') != 'Talk' or item.get('Options') for item in items[1:]):
        return None
    last = items[-1]
    if reached_talk_id != last.get('Id'):
        return None
    ops = last.get('Actions', [])
    if (last.get('Options') or len(ops) != 2
            or not synchronous(ops[0], 'FinishDoInteract') or ops[0].get('Params') != {}
            or ops[1] != boundary.source_action or ops[1].get('Params') != {}):
        return None
    # Earlier execution already reached this boundary. The enclosing parser
    # validates conditions and actions before returning any readable result.
    return {'kind': 'terminal_text_boundary', 'source_action': deepcopy(boundary.source_action),
            'last_talk_id': last['Id'], 'selected_text_complete': True,
            'state_controls_executed': False, 'runtime_completion_verified': False,
            'cross_segment_propagation': False,
            'basis': 'final item of final ShowTalk has no following local text'}
