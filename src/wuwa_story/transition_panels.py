"""Static async popup text is an attachment, never a serial dialogue event."""
import hashlib
import struct
from copy import deepcopy
from .database import field, integer, string, texts
from .rendering import render_text


def inspect_transition(action, read_rows):
    if (not isinstance(action, dict) or action.get('Name') != 'OpenSystemBoard'
            or set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            or action.get('Async') is not True):
        raise ValueError('Unsupported async transition execution parameters')
    p = action.get('Params')
    if (not isinstance(p, dict) or set(p) != {'SystemType', 'BoardId'}
            or p['SystemType'] != 'TransitionPopup' or type(p['BoardId']) is not int
            or p['BoardId'] <= 0):
        raise ValueError('Unsupported static transition reference')
    matches = [r for r in read_rows('db_TransitionPopup.db', 'transitionpopup') if r['Id'] == p['BoardId']]
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous transition definition')
    blob = matches[0]['BinData']
    try:
        root = struct.unpack_from('<I', blob)[0]
        vt = root - struct.unpack_from('<i', blob, root)[0]
        if (struct.unpack_from('<H', blob, vt)[0] != 12
                or any(field(blob, i) is None for i in range(4))
                or integer(blob, 0) != p['BoardId'] or integer(blob, 1) != 1):
            raise ValueError('Unsupported static transition layout or type')
        keys = [string(blob, 2), string(blob, 3)]
    except (struct.error, UnicodeError, TypeError, IndexError) as exc:
        raise ValueError('Invalid transition definition encoding') from exc
    values = []
    for index, key, purpose in zip((2, 3), keys, ('title', 'body')):
        raw = texts.get(key)
        if not key or not isinstance(raw, str) or not raw.strip():
            raise ValueError('Missing static transition text')
        rendered = render_text(raw)
        if any(c in rendered for c in '{}%'):
            raise ValueError('Unknown dynamic transition text')
        values.append({'text_id': key, 'raw_text': raw, 'text': rendered,
                       'purpose': purpose, 'source_field': index})
    return {'kind': 'async_transition_panel', 'board_id': p['BoardId'], 'panel_type': 1,
            'texts': values,
            'source': {'table': 'db_TransitionPopup.db/transitionpopup',
                       'sha256': hashlib.sha256(blob).hexdigest(),
                       'fields': {'id': 0, 'panel_type': 1, 'title': 2, 'body': 3}},
            'source_action': deepcopy(action),
            'call_anchor': {'action_id': action.get('ActionId'), 'action_guid': action.get('ActionGuid')},
            'async': True, 'display_order_verified': False,
            'interleaving_with_dialogue_verified': False, 'completion_verified': False,
            'runtime_executed': False,
            'handling': 'unordered_attachment_at_known_call',
            'note': 'Static text source and call anchor are known; async display timing is not a serial narrative order'}
