"""Resolve static letter panels through their explicit dialogue-flow reference."""
import hashlib
import struct
from .database import field, integer, string
from .phone import string_vector


def inspect_letter(action, read_rows, choices=None):
    from .export_task import Exporter, flow_actions
    from .rendering import render_result
    if (not isinstance(action, dict) or action.get('Name') != 'OpenSystemBoard'
            or set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            or action.get('Async', False) is not False):
        raise ValueError('Unsupported letter execution parameters')
    p = action.get('Params')
    if not isinstance(p, dict) or set(p) != {'SystemType', 'BoardId', 'WriteLetterConfig'}:
        raise ValueError('Unsupported letter parameters')
    config = p['WriteLetterConfig']
    if (p['SystemType'] != 'WriteLetter' or type(p['BoardId']) is not int or p['BoardId'] != 0
            or not isinstance(config, dict) or set(config) != {'LetterId'}
            or type(config['LetterId']) is not int or config['LetterId'] <= 0):
        raise ValueError('Unsupported letter reference')

    def one(db, table, key, value):
        matches = [r for r in read_rows(db, table) if r[key] == value]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous letter reference: ' + str(value))
        return matches[0]

    row = one('db_WriteLetter.db', 'writeletter', 'Id', config['LetterId'])
    blob = row['BinData']
    try:
        root = struct.unpack_from('<I', blob)[0]
        vt = root - struct.unpack_from('<i', blob, root)[0]
        if (struct.unpack_from('<H', blob, vt)[0] != 12
                or any(field(blob, i) is None for i in range(4))
                or integer(blob, 0) != config['LetterId']):
            raise ValueError('Unsupported letter definition layout')
        style, title, flow = string(blob, 1), string(blob, 3), string_vector(blob, 2)
    except (struct.error, UnicodeError, TypeError, IndexError) as exc:
        raise ValueError('Invalid letter definition encoding') from exc
    if (not style or not title or any(c in style + title for c in '{}%')
            or len(flow) != 3 or not flow[0] or not all(v.isdecimal() and int(v) > 0 for v in flow[1:])):
        raise ValueError('Unsupported letter flow reference or dynamic title')
    key = f'{flow[0]}_{int(flow[1])}_{int(flow[2])}'
    state = one('db_flowState.db', 'flowstate', 'StateKey', key)
    actions, fields = flow_actions(state['BinData'])
    # Letter composition and nested UI/flow callbacks are not ordinary reading.
    # Limit to the observed static panel setup and text-only ShowTalk shape.
    if (len(actions) != 2 or not all(isinstance(a, dict) for a in actions)
            or [a.get('Name') for a in actions] != ['SetPlotMode', 'ShowTalk']):
        raise ValueError('Letter flow is not static text')
    for a in actions:
        if (set(a) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
                or a.get('Async', False) is not False):
            raise ValueError('Unsupported letter flow execution fields')
    mode = actions[0].get('Params')
    if (not isinstance(mode, dict) or set(mode) != {'Mode', 'IsSwitchMainRole'}
            or mode['Mode'] != 'LevelC' or type(mode['IsSwitchMainRole']) is not bool):
        raise ValueError('Unsupported letter flow setup')
    talks = actions[1].get('Params')
    if not isinstance(talks, dict) or set(talks) != {'TalkItems'} or not isinstance(talks['TalkItems'], list) or not talks['TalkItems']:
        raise ValueError('Missing letter text')
    for item in talks['TalkItems']:
        if (not isinstance(item, dict)
                or set(item) - {'Type', 'Id', 'PlotLineId', 'Name', 'WhoId', 'TextId', 'TidTalk', 'PlotLineKey'}
                or item.get('Type') != 'Talk' or type(item.get('WhoId')) is not int
                or not isinstance(item.get('TidTalk'), str) or not item['TidTalk']):
            raise ValueError('Unsupported letter dialogue controls')
    child = Exporter(choices=choices)
    child.rows = read_rows
    child.state_key = key
    if child.actions(actions):
        raise ValueError('Unexpected letter control transfer')
    rendered = render_result({'title': '', 'route': {'choices': child.decisions}, 'events': child.events})
    if any(any(c in e['text'] for c in '{}%') for e in rendered['events']):
        raise ValueError('Unsupported dynamic letter text')
    return {'letter_id': config['LetterId'], 'state_key': key, 'title': title,
            'style': style, 'style_identity_inferred': False,
            'source': {'table': 'db_WriteLetter.db/writeletter',
                       'sha256': hashlib.sha256(blob).hexdigest(),
                       'flow_table': 'db_flowState.db/flowstate',
                       'flow_sha256': hashlib.sha256(state['BinData']).hexdigest(),
                       'fields': {'id': 0, 'style': 1, 'flow_reference': 2, 'title': 3},
                       'equivalent_action_fields': fields},
            'events': rendered['events'], 'route': rendered['route'],
            'missing_text_ids': child.missing, 'action_trace': child.action_log,
            'read_completion_verified': False, 'close_completion_verified': False}
