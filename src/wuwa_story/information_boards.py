"""InformationView: exact BoardId -> info display -> explicit localized keys."""
import hashlib
from .database import string, texts
from .rendering import render_text


def inspect_information(board_id, read_rows):
    if type(board_id) is not int:
        raise ValueError('InformationView BoardId must be integer')
    matches = [r for r in read_rows('db_infodisplay.db', 'infodisplay') if r['Id'] == board_id]
    if len(matches) != 1:
        raise ValueError('InformationView row is missing or ambiguous')
    row = matches[0]
    values = []
    for field, purpose in ((3, 'title'), (4, 'body')):
        key = string(row['BinData'], field)
        if not key:
            raise ValueError('InformationView text key missing')
        raw = texts.get(key)
        values.append({'text_id': key, 'purpose': purpose, 'source_field': field,
                       'raw_text': raw, 'text': render_text(raw) if raw is not None else '[缺失文本：'+key+']',
                       'missing': raw is None})
    return {'board_id': board_id, 'item_id': row['ItemId'],
            'source_table': 'db_infodisplay.db/infodisplay',
            'sha256': hashlib.sha256(row['BinData']).hexdigest(),
            'texts': values, 'display_timing_verified': False,
            'missing_text_ids': [v['text_id'] for v in values if v['missing']]}
