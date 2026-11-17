"""Compare text provenance, not raw line counts or guessed narrative order."""
from collections import Counter, defaultdict


def compare_extractions(ours, other):
    events = list(ours.get('events', []))
    segments = ours.get('recap_backbone', {}).get('segments', [])
    events += [e for s in segments for e in s['events']]
    own = {(e.get('state_key'), e['text_id']) for e in events if e.get('text_id')}
    own |= {(r['origin'], r['text_id']) for r in ours['batch_coverage']['records']
            if r.get('origin') and r.get('text_id')}
    external = []
    for line in other['all_lines']:
        if line.get('text_key'):
            external.append({'state_key': line['state_key'], 'text_id': line['text_key'],
                             'raw_text': line.get('text_zh-Hans', ''), 'kind': line.get('type'),
                             'source': 'item'})
        for option in line.get('options', []):
            if option.get('text_key'):
                external.append({'state_key': line['state_key'], 'text_id': option['text_key'],
                                 'raw_text': option.get('text_zh-Hans', ''), 'kind': 'Option',
                                 'source': 'option'})
    foreign = {(e['state_key'], e['text_id']) for e in external}
    order = list(dict.fromkeys(e['state_key'] for e in other['all_lines']))
    positions = {key: i for i, key in enumerate(order)}
    multiplicity = Counter(s['state_key'] for s in segments)
    order_checks = []
    for a, b in zip(segments, segments[1:]):
        ka, kb = a['state_key'], b['state_key']
        status = 'unresolved'
        if multiplicity[ka] == multiplicity[kb] == 1 and ka in positions and kb in positions:
            status = 'consistent' if positions[ka] < positions[kb] else 'reversed'
        order_checks.append({'before': ka, 'after': kb, 'status': status})
    return {'count_unit': 'unique (state_key, text_id); not occurrence count or completeness',
            'ours_unique': len(own), 'reference_unique': len(foreign), 'shared': len(own & foreign),
            'reference_only': [e for e in external if (e['state_key'], e['text_id']) not in own],
            'reference_only_unique': len(foreign - own),
            'ours_only': [{'state_key': s, 'text_id': t} for s, t in sorted(own-foreign)],
            'adjacent_recap_order_checks': order_checks,
            'order_summary': dict(Counter(c['status'] for c in order_checks)),
            'note': 'Inventory membership does not prove execution. Recap comparison is not runtime verification.'}
