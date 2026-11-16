"""Classify speech references by node semantics, never by missing-key prefixes."""


def option_container(item):
    return (item.get('Type') == 'Option'
            and not item.get('PlotLineKey') and 'TextId' not in item)


def non_dialogue_reason(item):
    if option_container(item):
        return 'option_control_container'
    if item.get('Type') == 'NoTextItem':
        return 'explicit_no_text_item'
    if item.get('Type') == 'QTE':
        return 'qte_control_not_speech'
    return None


def control_references(value, text_map, path=()):
    """Keep suppressed keys, source nodes, actions and QTE outcomes in JSON."""
    out = []
    if isinstance(value, dict):
        reason = non_dialogue_reason(value)
        if reason:
            key = value.get('TidTalk')
            out.append({'source_path': list(path), 'reason': reason,
                        'text_id': key, 'text_present': key in text_map,
                        'raw_text': text_map.get(key), 'source_item': value,
                        'runtime_verified': False})
        for key, child in value.items():
            out.extend(control_references(child, text_map, path + (key,)))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            out.extend(control_references(child, text_map, path + (i,)))
    return out
