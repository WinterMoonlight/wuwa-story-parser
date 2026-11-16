"""Inventory Reigns text and branch evidence without inventing a winning route."""
import hashlib
from .database import string, embedded, texts
from .phone import string_vector
from .export_task import walk, flow_actions
from .reigns_rules import audit_rules


def inspect_reigns(config, read_rows):
    if set(config) != {'Type', 'ReignsId'} or config['Type'] != 'Reigns':
        raise ValueError('Unsupported simple gameplay configuration')
    def one(db, table, key, value):
        matches = [r for r in read_rows(db, table) if r[key] == value]
        if len(matches) != 1:
            raise ValueError(f'Missing or ambiguous gameplay reference: {table}/{value}')
        return matches[0]
    row = one('db_Reigns.db', 'reigns', 'Id', config['ReignsId'])
    ref = string_vector(row['BinData'], 5)
    if len(ref) != 3 or not ref[1].isdigit() or not ref[2].isdigit():
        raise ValueError('Invalid Reigns flow reference')
    key = '_'.join(ref)
    state = one('db_flowState.db', 'flowstate', 'StateKey', key)
    actions, fields = flow_actions(state['BinData'])
    result_texts = []
    def collect(value, path):
        if isinstance(value, dict):
            for k, v in value.items():
                if k in {'TidTalk', 'TidTalkOption', 'TidCenterText'} and v:
                    result_texts.append({'text_id': v, 'raw_text': texts.get(v), 'missing': v not in texts,
                                         'source_path': path + [k], 'source': key, 'who_id': value.get('WhoId')})
                else:
                    collect(v, path + [k])
        elif isinstance(value, list):
            for i, v in enumerate(value): collect(v, path + [i])
    collect(actions, [])
    data = dict(embedded(row['BinData']))
    endings = data.get(6)
    if not isinstance(endings, list):
        raise ValueError('Missing Reigns ending conditions')
    cards = []
    # Direct card calls are separate from ending cards and must also be collected.
    direct_calls = [a for a in walk(actions) if a.get('Name') == 'ReignsCallCard']
    card_ids = {v for e in endings for v in ([e['CardId']] if e.get('CardId') else []) + e.get('CardIds', [])}
    card_ids.update(a['Params']['CardId'] for a in direct_calls)
    for cid in sorted(card_ids):
        matches = [r for r in read_rows('db_ReignsCard.db', 'reignscard') if r['Id'] == cid]
        if not matches:
            cards.append({'card_id': cid, 'status': 'reference_unresolved'})
            continue
        if len(matches) != 1: raise ValueError('Ambiguous Reigns card')
        card = matches[0]
        cards.append({'card_id': cid, 'status': 'read', 'sha256': hashlib.sha256(card['BinData']).hexdigest()})
        for i, suffix in ((4, 'CardTitle'), (5, 'CardDesc'), (6, 'CardHeader')):
            legacy = string(card['BinData'], i)
            text_key = f'ReignsCard_{cid}_{suffix}'
            localized = text_key in texts
            text = texts[text_key] if localized else legacy
            if text or legacy:
                result_texts.append({'text_id': text_key if localized else None, 'raw_text': text,
                                     'legacy_inline_text': legacy, 'missing': False,
                                     'localization_basis': 'Matching ReignsCard ID and field-name key' if localized else 'Inline fallback; localization key absent',
                                     'source': 'db_ReignsCard.db/reignscard', 'card_id': cid, 'source_field': i})
    return {'reigns_id': config['ReignsId'], 'state_key': key, 'source_actions': actions,
            'action_fields': fields, 'endings': endings, 'initial_properties': data.get(7), 'cards': cards,
            'direct_card_calls': direct_calls,
            'mechanics_audit': audit_rules(actions, endings, data.get(7, [])),
            'property_names': {str(p['Id']): texts.get(f"ReignsAttribute_{p['Id']}_Name") for p in data.get(7, [])},
            'sha256': hashlib.sha256(row['BinData']).hexdigest(),
            'flow_sha256': hashlib.sha256(state['BinData']).hexdigest(),
            'texts': result_texts, 'route_simulated': False}
