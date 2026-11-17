"""Decode only proven static, single-button confirmation panels."""
import hashlib
import struct
from .database import field, integer, string, texts


def inspect_confirm_box(action, read_rows):
    if (set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            or action.get('Async', False) is not False):
        raise ValueError('Unsupported ConfirmBox execution parameters')
    p = action.get('Params', {})
    if set(p) != {'SystemType', 'BoardId'} or p['SystemType'] != 'ConfirmBox' or type(p['BoardId']) is not int:
        raise ValueError('Unsupported ConfirmBox parameters')
    matches = [r for r in read_rows('db_confirmbox.db', 'confirmbox') if r['Id'] == p['BoardId']]
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous ConfirmBox')
    b = matches[0]['BinData']
    try:
        root = struct.unpack_from('<I', b)[0]
        vt = root - struct.unpack_from('<i', b, root)[0]
        if struct.unpack_from('<H', b, vt)[0] != 14 or integer(b, 0) != p['BoardId'] or string(b, 3):
            raise ValueError('Unknown ConfirmBox layout or dynamic content')
        pos = field(b, 4)
        q = pos + struct.unpack_from('<I', b, pos)[0]
        if struct.unpack_from('<I', b, q)[0] != 1:
            raise ValueError('ConfirmBox must have one static button')
        pos = q + 4
        q = pos + struct.unpack_from('<I', b, pos)[0]
        size = struct.unpack_from('<I', b, q)[0]
        if q + 4 + size > len(b):
            raise ValueError('Invalid button string')
        button = b[q+4:q+4+size].decode('utf-8')
        keys = [string(b, 1), string(b, 2), button]
    except (struct.error, TypeError, UnicodeError) as exc:
        raise ValueError('Invalid ConfirmBox encoding') from exc
    values = []
    for key, purpose in zip(keys, ('title', 'body', 'button_label')):
        raw = texts.get(key)
        if not raw or any(c in raw for c in '{}%'):
            raise ValueError('Missing or dynamic ConfirmBox text')
        values.append({'text_id': key, 'raw_text': raw, 'purpose': purpose})
    return {'board_id': p['BoardId'], 'texts': values,
            'source_table': 'db_confirmbox.db/confirmbox',
            'sha256': hashlib.sha256(b).hexdigest(), 'button_click_verified': False,
            'runtime_completion_verified': False}
