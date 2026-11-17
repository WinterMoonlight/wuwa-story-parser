"""Read guide configuration references; never simulate display eligibility."""
import base64
import hashlib
import struct
from .database import integer, string, vec, texts
from .phone import string_vector


def inspect_guide(params, read_rows):
    if params.get('Type') != 'BeginnerGuide':
        raise ValueError('Unsupported guide trigger type')
    if set(params) - {'Type', 'GuideId', 'Conditions'}:
        raise ValueError('Unsupported guide trigger parameters')
    cache = {}
    def row(table, key, value):
        if table not in cache:
            cache[table] = read_rows('db_guide_new.db', table)
        matches = [r for r in cache[table] if r[key] == value]
        if len(matches) != 1:
            raise ValueError(f'Missing or ambiguous guide reference: {table}/{value}')
        return matches[0]
    def evidence(table, r):
        return {'table': 'db_guide_new.db/' + table,
                'row': {k: v for k, v in r.items() if k != 'BinData'},
                'sha256': hashlib.sha256(r['BinData']).hexdigest(),
                'bin_data_base64': base64.b64encode(r['BinData']).decode('ascii')}
    found = []
    def text_ref(table, r, field, step_id, purpose):
        key = string(r['BinData'], field)
        if not key:
            return
        candidates = {}
        for index in {'guidetips': (2, 3, 4), 'guidefocusnew': (14, 15, 16)}.get(table, ()):
            try:
                values = string_vector(r['BinData'], index)
            except (ValueError, UnicodeError, struct.error):
                continue
            if values and all(all(character.isprintable() for character in value) for value in values):
                candidates[str(index)] = values
        found.append({'text_id': key, 'raw_text': texts.get(key), 'missing': key not in texts,
                      'source_table': table, 'source_field': field, 'step_id': step_id,
                      'source_id': r.get('Id', r.get('GuideId')), 'purpose': purpose,
                      'format_argument_candidates': candidates})
    group = row('guidegroup', 'Id', params['GuideId'])
    step_ids = vec(group['BinData'], 1)
    steps = []
    for sid in step_ids:
        r = row('guidestep', 'Id', sid)
        code = integer(r['BinData'], 8)
        table = {1: 'guidetips', 4: 'guidefocusnew', 3: 'guidetutorial'}.get(code)
        if table is None:
            raise ValueError('Unsupported guide step type: ' + str(code))
        content = row(table, 'Id' if code == 3 else 'GuideId', sid)
        step = {'step_id': sid, 'type_code': code, 'platform_mask_raw': string(r['BinData'], 1),
                'step_source': evidence('guidestep', r), 'content_source': evidence(table, content),
                'display_verified': False}
        if code == 3:
            text_ref(table, content, 6, sid, 'tutorial_group_title')
            step['pages'] = []
            for page_id in vec(content['BinData'], 3):
                page = row('guidetutorialpage', 'Id', page_id)
                step['pages'].append({'page_id': page_id, 'source': evidence('guidetutorialpage', page),
                                      'image_asset': string(page['BinData'], 1)})
                text_ref('guidetutorialpage', page, 2, sid, 'page_title')
                text_ref('guidetutorialpage', page, 4, sid, 'page_body')
        else:
            text_ref(table, content, 1 if code == 1 else 13, sid, 'guide_body')
        steps.append(step)
    return {'group_id': params['GuideId'], 'group_source': evidence('guidegroup', group),
            'step_ids': step_ids, 'steps': steps, 'texts': found,
            'trigger_conditions': params.get('Conditions', []),
            'display_verified': False,
            'limitations': ['Platform masks retained without assigning platform names',
                            'Node, trigger and internal guide eligibility are not evaluated',
                            'Input argument vectors retained without choosing a platform or physical key',
                            'Undecoded display fields retained in source blobs']}
