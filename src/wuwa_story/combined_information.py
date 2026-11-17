"""Static panel calls whose dialogue branches agree with sequence metadata."""
from copy import deepcopy
import struct

from .database import integer, string
from .information_boards import inspect_information
from .rendering import render_text


ACTION_FIELDS = {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
OPTION_FIELDS = {'TidTalkOption', 'Actions', 'TextId', 'PlotLineId', 'PlotLineKey'}


def jump_target(actions):
    if not isinstance(actions, list) or len(actions) != 1:
        return None
    action = actions[0]
    if (not isinstance(action, dict) or set(action) - ACTION_FIELDS
            or action.get('Name') != 'JumpTalk' or action.get('Async', False) is not False):
        return None
    params = action.get('Params')
    if not isinstance(params, dict) or set(params) != {'TalkId'} or type(params['TalkId']) is not int:
        return None
    return params['TalkId']


def matching_dialogue_branches(item, params):
    """Require an exhaustive four-sequence diamond with matching jump edges."""
    if not isinstance(params, dict):
        return False
    items = params.get('TalkItems', [])
    groups = params.get('TalkSequence')
    names = params.get('SequenceNames')
    transitions = params.get('SequenceTransitions')
    if (not isinstance(groups, list) or len(groups) != 4
            or not all(isinstance(group, list) and group for group in groups)
            or not isinstance(names, list) or len(names) != 4
            or not all(isinstance(name, str) and name for name in names)
            or not isinstance(transitions, dict) or set(transitions) != {'0', '1', '2'}):
        return False
    if not isinstance(items, list) or not all(isinstance(node, dict) for node in items):
        return False
    ids = [node.get('Id') for node in items]
    flat = [value for group in groups for value in group]
    if (not all(type(value) is int for value in flat) or flat != ids
            or len(set(flat)) != len(flat) or item.get('Id') != groups[0][-1]):
        return False
    options = item.get('Options')
    if not isinstance(options, list) or len(options) != 2:
        return False
    expected = {}
    for index, option in enumerate(options, 1):
        if (not isinstance(option, dict) or set(option) - OPTION_FIELDS
                or not isinstance(option.get('TidTalkOption'), str) or not option['TidTalkOption']
                or jump_target(option.get('Actions')) != groups[index][0]):
            return False
        expected[index] = option['TidTalkOption']
    branch_edges = transitions['0']
    if not isinstance(branch_edges, list) or len(branch_edges) != 2:
        return False
    for index, edge in enumerate(branch_edges, 1):
        if (not isinstance(edge, dict) or set(edge) != {'NextSequenceIndex', 'OptionText', 'OptionTextKey'}
                or type(edge['NextSequenceIndex']) is not int or edge['NextSequenceIndex'] != index
                or edge['OptionTextKey'] != expected[index] or not isinstance(edge['OptionText'], str)):
            return False
    by_id = {node['Id']: node for node in items}
    for index in (1, 2):
        if transitions[str(index)] != [{'NextSequenceIndex': 3, 'OptionText': '', 'OptionTextKey': ''}]:
            return False
        if jump_target(by_id[groups[index][-1]].get('Actions')) != groups[3][0]:
            return False
    for index, group in enumerate(groups):
        for node_id in group:
            node = by_id[node_id]
            if node.get('Type') != 'Talk' or any('condition' in key.lower() for key in node):
                return False
            if node_id == item['Id']:
                continue
            if node.get('Actions') and not (index in (1, 2) and node_id == group[-1]):
                return False
            passive_options = node.get('Options', [])
            if not isinstance(passive_options, list):
                return False
            for option in passive_options:
                if (not isinstance(option, dict) or set(option) - OPTION_FIELDS
                        or not isinstance(option.get('TidTalkOption'), str) or not option['TidTalkOption']
                        or option.get('Actions', []) != []):
                    return False
    return True


def inspect_combined_information(item, params, read_rows):
    if not matching_dialogue_branches(item, params):
        raise ValueError('Combined information dialogue order is unverified')
    actions = item.get('Actions')
    if not isinstance(actions, list) or len(actions) != 1:
        raise ValueError('Combined information requires one static panel call')
    action = actions[0]
    if not isinstance(action, dict):
        raise ValueError('Combined information call must be an action object')
    p = action.get('Params')
    if (set(action) - ACTION_FIELDS or action.get('Name') != 'OpenSystemBoard'
            or action.get('Async') is not False or not isinstance(p, dict)
            or set(p) != {'SystemType', 'BoardId'} or p['SystemType'] != 'InformationView'
            or type(p['BoardId']) is not int or p['BoardId'] <= 0):
        raise ValueError('Combined information call shape is unverified')
    matches = [row for row in read_rows('db_infodisplay.db', 'infodisplay') if row['Id'] == p['BoardId']]
    if len(matches) != 1 or matches[0]['ItemId'] != 0:
        raise ValueError('Combined information definition is missing or dynamic')
    blob = matches[0]['BinData']
    root = struct.unpack_from('<I', blob)[0]
    vtable = root - struct.unpack_from('<i', blob, root)[0]
    if (struct.unpack_from('<HH', blob, vtable) != (24, 40)
            or [integer(blob, i) for i in range(3)] != [p['BoardId'], 0, 3]
            or any(string(blob, i) for i in range(5, 10))):
        raise ValueError('Combined information layout is unverified')
    board = inspect_information(p['BoardId'], read_rows)
    if board['missing_text_ids'] or any(not value['raw_text'].strip()
            or any(char in render_text(value['raw_text']) for char in '{}%') for value in board['texts']):
        raise ValueError('Combined information static text is unavailable')
    return {'kind': 'combined_information_panel', 'board_id': p['BoardId'],
            'texts': board['texts'], 'source': board, 'source_action': deepcopy(action),
            'call_anchor': {'talk_id': item['Id'], 'before_option_selection_in_config': True},
            'dialogue_order_evidence': {key: deepcopy(params[key]) for key in
                ('TalkSequence', 'SequenceNames', 'SequenceTransitions')},
            'display_order_verified': False, 'interleaving_with_dialogue_verified': False,
            'completion_verified': False, 'runtime_executed': False,
            'handling': 'attachment_at_known_talk_call'}
