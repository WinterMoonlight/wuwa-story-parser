"""Read a declared linear text path while leaving QTE execution unresolved."""
from copy import deepcopy
from itertools import groupby

from .terminal_text import synchronous


def configured_qte_sequence(action):
    if not synchronous(action, 'ShowTalk'):
        return None
    params = action.get('Params')
    if (not isinstance(params, dict) or set(params) - {
            'TalkItems', 'TalkSequence', 'SequenceNames', 'SequenceTransitions', 'SequenceDataAsset'}):
        return None
    if 'SequenceDataAsset' in params and not isinstance(params['SequenceDataAsset'], str):
        return None
    items, groups = params.get('TalkItems'), params.get('TalkSequence')
    names = params.get('SequenceNames')
    if (not isinstance(items, list) or not items or not all(isinstance(item, dict) for item in items)
            or not isinstance(groups, list) or len(groups) != 1 or not isinstance(groups[0], list)
            or not isinstance(names, list) or len(names) != 1
            or not isinstance(names[0], str) or not names[0]
            or params.get('SequenceTransitions') != {}):
        return None
    ids = [item.get('Id') for item in items]
    sequence = groups[0]
    if (any(type(value) is not int for value in ids + sequence)
            or len(set(ids)) != len(ids) or len(set(sequence)) != len(sequence)
            or set(ids) != set(sequence)):
        return None
    common = {'Type', 'Id', 'Name', 'TextId', 'TidTalk', 'PlotLineKey', 'PlotLineId', 'WhoId', 'Actions', 'Options'}
    talk_fields = common | {'PlayVoice', 'TalkAkEvent', 'Style', 'ActorLookAtArray', 'ActorMontageArray'}
    has_qte = False
    from .export_task import walk
    for item in items:
        if (not isinstance(item.get('Actions', []), list) or item.get('Actions')
                or not isinstance(item.get('Options', []), list) or item.get('Options')):
            return None
        for value in walk(item):
            if any('condition' in key.lower() for key in value):
                return None
            if 'Name' in value and 'Params' in value:
                return None
        if item.get('Type') == 'QTE':
            if (set(item) - (common | {'QteId'}) or type(item.get('QteId')) is not int
                    or item['QteId'] <= 0):
                return None
            has_qte = True
        elif item.get('Type') == 'Talk':
            if (set(item) - talk_fields or not isinstance(item.get('TidTalk'), str)
                    or not item['TidTalk']):
                return None
        else:
            return None
    if not has_qte:
        return None
    by_id = {item['Id']: item for item in items}
    return [by_id[value] for value in sequence]


def append_configured_qte_text(parser, action):
    """Commit only the declared text order, with no simulated QTE result."""
    ordered = configured_qte_sequence(action)
    if ordered is None:
        return False
    text_items = [item for item in ordered if item['Type'] == 'Talk']
    start = len(parser.events)
    # Empty QTE-only groups still occupy their original ShowTalk position.
    parser.talk(text_items)
    text_events = parser.events[start:]
    if len(text_events) != len(text_items):
        raise ValueError('Linear QTE text projection produced unexpected events')
    events = iter(text_events)
    result = []
    for is_qte, group in groupby(ordered, key=lambda item: item['Type'] == 'QTE'):
        values = list(group)
        if is_qte:
            result.append({'kind': 'qte_reference', 'state_key': parser.state_key,
                           'talk_group': parser.talk_groups[parser.state_key],
                           'raw_text': '【快速反应操作】后续按配置继续路径排列，操作结果未模拟。',
                           'source_items': deepcopy(values), 'content_deferred': True})
        else:
            result.extend(next(events) for _ in values)
    parser.events[start:] = result
    parser.unverified_content.append({
        'kind': 'configured_qte_text_order', 'source_action': deepcopy(action),
        'declared_talk_ids': [item['Id'] for item in ordered],
        'ordered_text_ids': [item['Id'] for item in text_items],
        'qte_ids': [item['QteId'] for item in ordered if item['Type'] == 'QTE'],
        'text_order_basis': 'single exhaustive TalkSequence with no outcome edges or item actions',
        'continuation_condition': 'QTE returns along the declared configuration sequence',
        'local_text_order_verified': True, 'runtime_return_verified': False,
        'qte_result_selected': False, 'all_runtime_outcomes_verified': False,
        'external_asset_content_in_scope': False})
    return True
