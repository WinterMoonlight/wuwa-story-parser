"""QTE control references are not dialogue or evidence of successful execution."""


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
