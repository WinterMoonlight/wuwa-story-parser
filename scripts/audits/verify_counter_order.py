"""Check local-order recovery against the preceding mainline reading batch."""
import argparse
from collections import Counter
import json
from pathlib import Path

from wuwa_story.mainline_reading import build_mainline_reading, mainline_reading_text


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def source_texts(document):
    values = set()

    def visit(value):
        if isinstance(value, dict):
            if value.get('text_id') and 'text' in value:
                values.add((value['text_id'], value.get('raw_text', value['text'])))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(document)
    return values


def verify(baseline, batch):
    old_report, report = load(baseline / '覆盖报告.json'), load(batch / '覆盖报告.json')
    assert old_report['source_sha256'] == report['source_sha256']
    old_tasks = {task['quest_id']: task for task in old_report['tasks']}
    changed, counters = [], []
    for task in report['tasks']:
        old = load(baseline / old_tasks[task['quest_id']]['files'][0])
        new = load(batch / task['files'][0])
        for field in ('source', 'events', 'route', 'recap_backbone'):
            assert old.get(field) == new.get(field), (task['quest_id'], field)
        assert source_texts(old) <= source_texts(new), (task['quest_id'], 'source text lost')
        old_parts = [part for block in old['mainline_reading']['blocks'] for part in block['parts']]
        new_parts = [part for block in new['mainline_reading']['blocks'] for part in block['parts']]
        cursor = 0
        for part in new_parts:
            if cursor < len(old_parts) and part == old_parts[cursor]:
                cursor += 1
        assert cursor == len(old_parts), (task['quest_id'], 'old reading order changed')
        assert new['mainline_reading'] == build_mainline_reading(new)
        text = (batch / task['files'][1]).read_text(encoding='utf-8-sig')
        assert text == mainline_reading_text(new)
        for group in new['batch_coverage']['levelplay_local_sequences']:
            if group.get('order_scope') != 'increasing_counter_invocations':
                continue
            proof = group['proof']
            thresholds = [item['threshold'] for item in proof['thresholds']]
            assert thresholds == sorted(set(thresholds))
            assert all(item['increment'] > 0 for item in proof['positive_writes'])
            assert not group['placement_verified'] and not group['runtime_verified']
            assert not proof['initial_value_assumed'] and not proof['all_thresholds_reached_verified']
            counters.append({'quest_id': task['quest_id'], 'levelplay_id': group['levelplay_id'],
                             'state_keys': group['state_keys'], 'thresholds': thresholds})
        if text != (baseline / old_tasks[task['quest_id']]['files'][1]).read_text(encoding='utf-8-sig'):
            changed.append({'quest_id': task['quest_id'], 'title': task['title'],
                            'before': old['mainline_reading']['retained_text_events'],
                            'after': new['mainline_reading']['retained_text_events']})
    result = {'pairs_checked': len(report['tasks']), 'database_hashes_unchanged': True,
              'existing_mainline_routes_unchanged': True, 'source_texts_preserved': True,
              'previous_reading_parts_preserved_in_order': True,
              'counter_groups': counters, 'changed_readings': changed,
              'mainline_status': dict(Counter(load(batch / task['files'][0])['mainline_reading']['status']
                                             for task in report['tasks'] if task['type_id'] == 1))}
    (batch / '复杂任务顺序核对.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('batch', type=Path)
    args = parser.parse_args()
    verify(args.baseline, args.batch)
