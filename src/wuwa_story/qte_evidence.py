"""QTE control references are not dialogue or evidence of successful execution."""
from copy import deepcopy


def linear_qte_prefix(params):
    items = params.get('TalkItems', [])
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        return None
    if not any(item.get('Type') == 'QTE' for item in items):
        return None
    ids = [item.get('Id') for item in items]
    if (not items or any(type(value) is not int for value in ids)
            or len(set(ids)) != len(ids) or params.get('TalkSequence') != [ids]
            or not isinstance(params.get('SequenceNames'), list) or len(params['SequenceNames']) != 1
            or params.get('SequenceTransitions') != {}):
        return None
    stop = next((index for index, item in enumerate(items) if item.get('Type') == 'QTE'), 0)
    if not stop or any(item.get('Type') != 'Talk' for item in items[:stop]):
        return None
    if any(item.get('Type') != 'QTE' for item in items[stop:]):
        return None
    from .export_task import walk
    if any(item.get('Actions') or item.get('Options') for item in items):
        return None
    if any(any('condition' in key.lower() for key in value) for value in walk(items)):
        return None
    return items[:stop]


class UnresolvedQteBoundary(ValueError):
    def __init__(self, action, state_key):
        self.source_action = deepcopy(action)
        self.state_key = state_key
        super().__init__('QTE runtime outcome evaluator is unsupported')

    def as_dict(self):
        from .database import texts
        params = self.source_action['Params']
        return {'kind': 'unresolved_qte_boundary', 'state_key': self.state_key,
                'action': 'ShowTalk', 'source_action': self.source_action,
                'qte': inspect_qte(params, texts), 'boundary_executed': False,
                'suffix_order_verified': False, 'runtime_completion_verified': False,
                'prefix_order_basis': 'explicit_linear_talk_sequence_before_first_qte'}


def inspect_qte(params, text_map):
    items = params.get('TalkItems', [])
    ids = [i.get('Id') for i in items]
    sequence = params.get('TalkSequence')
    linear = len(set(ids)) == len(ids) and sequence == [ids]
    records = []
    for index, item in enumerate(items):
        if item.get('Type') != 'QTE':
            continue
        key = item.get('TidTalk')
        present = key in text_map
        value = text_map.get(key)
        records.append({'qte_id': item.get('QteId'), 'talk_id': item.get('Id'),
            'configured_index': index if linear else None, 'text_id': key,
            'text_status': 'missing' if not present else 'empty' if value == '' else 'present',
            'raw_text': value, 'source_item': item,
            'outcome_mapping_status': 'unresolved', 'runtime_order_verified': False})
    return {'items': records, 'explicit_linear_sequence': linear,
            'sequence_data_asset': params.get('SequenceDataAsset'),
            'sequence_names': params.get('SequenceNames', []),
            'sequence_transitions': params.get('SequenceTransitions'),
            'source_talk_sequence': sequence,
            'configured_order_is_runtime_route': False,
            'complete': False}
