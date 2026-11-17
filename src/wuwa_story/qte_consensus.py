"""Read text common to every explicitly mapped QTE outcome path."""
from copy import deepcopy
from .combined_information import jump_target
from .terminal_text import synchronous


def consensus_projection(action, text_map):
    if not synchronous(action, 'ShowTalk'):
        return None
    params = action.get('Params', {})
    if not isinstance(params, dict) or set(params) - {'TalkItems','TalkSequence','SequenceTransitions','SequenceNames','SequenceDataAsset'}:
        return None
    items, groups = params.get('TalkItems'), params.get('TalkSequence')
    transitions, names = params.get('SequenceTransitions'), params.get('SequenceNames')
    if (not isinstance(items, list) or not items or not all(isinstance(item, dict) for item in items)
            or not isinstance(groups, list) or not groups
            or not all(isinstance(group, list) and group for group in groups)
            or not isinstance(names, list) or len(names) != len(groups)
            or not isinstance(transitions, dict)):
        return None
    ids = [item.get('Id') for item in items]
    flat = [value for group in groups for value in group]
    if any(type(value) is not int for value in ids) or len(set(ids)) != len(ids) or len(set(flat)) != len(flat) or set(ids) != set(flat):
        return None
    from .export_task import walk
    if any(any('condition' in key.lower() for key in value) for value in walk(items)):
        return None
    by_id = {item['Id']: item for item in items}
    starts = {group[0]: index for index, group in enumerate(groups)}
    edges, qtes, terminals = {}, [], []
    used_transitions = set()
    for group_index, group in enumerate(groups):
        for offset, item_id in enumerate(group):
            item = by_id[item_id]
            if set(item) - {'Id','Name','Options','Actions','PlotLineKey','PlotLineId','QteId','TextId','TidTalk','Type','WhoId'}:
                return None
            kind = item.get('Type')
            last = offset == len(group) - 1
            successors = []
            if kind == 'QTE':
                options = item.get('Options')
                if not last or item.get('Actions') or not isinstance(options, list) or len(options) != 2:
                    return None
                if any(not isinstance(option, dict) or not isinstance(option.get('TypeParams'), dict)
                       or set(option['TypeParams']) != {'Type'} for option in options):
                    return None
                if {option['TypeParams']['Type'] for option in options} != {'QteSucceed', 'QteFailed'}:
                    return None
                expected = []
                for option in options:
                    if set(option) - {'Actions','PlotLineKey','ReadMarkEnabled','TextId','TidTalkOption','TypeParams'}:
                        return None
                    target = jump_target(option.get('Actions'))
                    if target not in starts:
                        return None
                    key = option.get('TidTalkOption')
                    if key not in text_map or text_map[key] != '':
                        return None
                    successors.append(target)
                    expected.append((starts[target], key))
                qtes.append(item_id)
            elif kind == 'NoTextItem':
                target = jump_target(item.get('Actions'))
                if not last or item.get('Options') or target not in starts or item.get('PlotLineKey'):
                    return None
                successors = [target]
                expected = [(starts[target], '')]
            elif kind == 'Talk':
                if item.get('Actions') or item.get('Options') or item.get('TidTalk') not in text_map:
                    return None
                if not last:
                    successors = [group[offset+1]]
                else:
                    terminals.append(item_id)
                expected = []
            else:
                return None
            if last and expected:
                key = str(group_index)
                configured = transitions.get(key)
                if not isinstance(configured, list) or len(configured) != len(expected):
                    return None
                actual = []
                for edge in configured:
                    if (not isinstance(edge, dict) or set(edge) != {'NextSequenceIndex','OptionText','OptionTextKey'}
                            or type(edge['NextSequenceIndex']) is not int):
                        return None
                    actual.append((edge['NextSequenceIndex'], edge['OptionTextKey']))
                if actual != expected:
                    return None
                used_transitions.add(key)
            edges[item_id] = successors
    if not qtes or len(terminals) != 1 or set(transitions) != used_transitions:
        return None
    if len(items) > 256:
        return None
    paths = []
    def traverse(node, seen, speech):
        if node in seen or len(paths) >= 256:
            raise ValueError('Cyclic or excessive QTE paths')
        seen = seen + [node]
        if by_id[node]['Type'] == 'Talk':
            speech = speech + [node]
        if not edges[node]:
            paths.append((seen, speech))
        for target in edges[node]:
            traverse(target, seen, speech)
    try:
        traverse(groups[0][0], [], [])
    except ValueError:
        return None
    if not paths or set(node for path, _ in paths for node in path) != set(ids):
        return None
    signatures = {tuple((by_id[node].get('TidTalk'), by_id[node].get('WhoId'), text_map[by_id[node]['TidTalk']])
                        for node in speech) for _, speech in paths}
    if len(signatures) != 1 or not paths[0][1]:
        return None
    selected_items = [deepcopy(by_id[node]) for node in paths[0][1]]
    proof = {'kind': 'qte_outcome_text_consensus', 'outcome_path_count': len(paths),
             'qte_talk_ids': qtes, 'paths': [path for path, _ in paths],
             'selected_text_complete': True, 'all_declared_outcomes_same_text': True,
             'runtime_completion_verified': False, 'qte_result_selected': False,
             'scope': 'local text conditional on return through a declared QTE outcome'}
    return selected_items, proof
