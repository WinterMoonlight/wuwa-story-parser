"""Independent recap segments: preserve explicit order without claiming task execution."""
import hashlib
from .database import embedded
from .export_task import Exporter, flow_key, flow_actions
from .rendering import render_result


def build_backbone(quest_id, handbook_rows, states, source):
    if len(handbook_rows) != 1:
        return None
    row = handbook_rows[0]
    arrays = [v for _, v in embedded(row['BinData']) if isinstance(v, list)]
    if len(arrays) != 1:
        return None
    entries = arrays[0]
    flows = [(i, e) for i, e in enumerate(entries) if e.get('Flow', {}).get('FlowListName')]
    if not flows:
        return None
    from .speakers import SpeakerResolver
    names = getattr(source, '_recap_speaker_records', None)
    if names is None:
        names = SpeakerResolver().records
        if source is not None:
            source._recap_speaker_records = names
    segments = []
    for i, entry in flows:
        key = flow_key(entry['Flow'])
        segment = {'entry_index': i, 'state_key': key, 'source_entry': entry,
                   'status': 'blocked', 'events': []}
        try:
            if key not in states:
                raise ValueError('Missing flow state')
            blob = states[key]['BinData']
            segment['sha256'] = hashlib.sha256(blob).hexdigest()
            actions, fields = flow_actions(blob)
            segment.update(source_actions=actions, equivalent_action_fields=fields)
            # Each occurrence gets a fresh parser: no leaked actor, option, or partial state.
            parser = Exporter(source=source, allow_incomplete=True, speaker_records=names)
            parser.state_key = key
            if parser.actions(actions):
                raise ValueError('Unexpected control outside dialogue')
            rendered = render_result({'title': '', 'route': {'choices': parser.decisions},
                                      'events': parser.events})
            segment.update(status='parsed', events=rendered['events'],
                           route=rendered['route'], action_trace=parser.action_log,
                           talk_groups=parser.talk_coverage,
                           unverified_content=parser.unverified_content,
                           missing_text_ids=sorted(set(parser.missing)))
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            segment['error'] = str(exc)
            segment['events'] = [{'kind': 'recap_gap', 'display_name': '缺口',
                                  'text': f'【回顾第{len(segments)+1}段暂未解析，后续正文继续】',
                                  'state_key': key}]
        segments.append(segment)
    if not any(s['status'] == 'parsed' and s['events'] for s in segments):
        return None
    return {'quest_id': quest_id, 'status': 'recap_draft',
            'order_source': {'database': 'db_PlotHandBook.db', 'table': 'plothandbookconfig',
                             'sha256': hashlib.sha256(row['BinData']).hexdigest(), 'entries': entries},
            'segments': segments,
            'parsed_segments': sum(s['status'] == 'parsed' for s in segments),
            'blocked_segments': sum(s['status'] == 'blocked' for s in segments),
            'task_order_verified': False, 'accepted': False}


def duplicate_text_flows(inventories, recap_keys, states):
    """Only fold extra-source text; never collapse repeated recap occurrences."""
    groups = {}
    duplicates = []
    for key in sorted(inventories, key=lambda k: (k not in recap_keys, k)):
        records = inventories[key]
        # Match full ordered text inventory including IDs, types and speakers, not fuzzy prose.
        signature = tuple((r['text_id'], r['raw_text'], r.get('kind'), r.get('who_id')) for r in records)
        if not signature or not any(r.get('text') for r in records):
            continue
        if signature in groups and key not in recap_keys:
            canonical = groups[signature]
            a, _ = flow_actions(states[canonical]['BinData'])
            b, _ = flow_actions(states[key]['BinData'])
            duplicates.append({'state_key': key, 'text_duplicate_of': canonical,
                               'text_occurrences': len(records), 'actions_equal': a == b,
                               'source_sha256': hashlib.sha256(states[key]['BinData']).hexdigest(),
                               'canonical_sha256': hashlib.sha256(states[canonical]['BinData']).hexdigest(),
                               'runtime_equivalence_verified': False})
        else:
            groups.setdefault(signature, key)
    return duplicates


def export_task_backbone(quest_id, choices=None):
    from .batch import Snapshot
    from .reading_batch import analyze
    source = Snapshot()
    quest = next(embedded(r['BinData'])[0][1] for r in source.rows('db_QuestData.db', 'questdata')
                 if r['QuestId'] == quest_id)
    nodes = [embedded(r['BinData'])[0][1] for r in source.rows('db_QuestNodeData.db', 'questnodedata')
             if r['Key'].startswith(str(quest_id) + '_')]
    books = {quest_id: [r for r in source.rows('db_PlotHandBook.db', 'plothandbookconfig')
                       if r['QuestId'] == quest_id]}
    states = {r['StateKey']: r for r in source.rows('db_flowState.db', 'flowstate')}
    # This entry point does not run the strict audit; do not claim a strict success.
    return analyze(quest, nodes, states, books, source, {'status': 'not_checked'}, choices=choices)


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    from .export_task import write_result
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--quest-id', type=int, required=True)
    parser.add_argument('--output', type=Path, default=Path('outputs/回顾主干验证'))
    parser.add_argument('--choices', type=Path, help='JSON mapping of choice keys to selected indices')
    args = parser.parse_args()
    import json
    choices = json.loads(args.choices.read_text(encoding='utf-8-sig')) if args.choices else None
    write_result(export_task_backbone(args.quest_id, choices), args.output)
