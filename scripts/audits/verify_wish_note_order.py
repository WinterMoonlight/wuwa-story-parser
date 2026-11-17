import json
import sys
from pathlib import Path

from wuwa_story.mainline_reading import build_mainline_reading, mainline_reading_text


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def at(document, pointer):
    value = document
    for key in pointer.strip('/').split('/'):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def segments(document):
    return {s['state_key']: s for g in document.get('task_local_sequences', []) for s in g['segments']}


baseline, current = map(Path, sys.argv[1:])
before, after = (load(root / '覆盖报告.json') for root in (baseline, current))
assert before['source_sha256'] == after['source_sha256']
old_tasks = {t['quest_id']: t for t in before['tasks']}
assert set(old_tasks) == {t['quest_id'] for t in after['tasks']}
changes, pointers, unchanged_txt = [], 0, 0
for task in after['tasks']:
    qid = task['quest_id']
    old = load(baseline / old_tasks[qid]['files'][0])
    new = load(current / task['files'][0])
    for key in ('source', 'events', 'route', 'recap_backbone', 'external_content'):
        assert old.get(key) == new.get(key), (qid, key)
    assert segments(old) == segments(new), (qid, 'flow contents/choices changed')
    assert new['mainline_reading']['status'] == old['mainline_reading']['status'], qid
    assert new['mainline_reading'] == build_mainline_reading(new), qid
    text = (current / task['files'][1]).read_text(encoding='utf-8-sig')
    assert text == mainline_reading_text(new), qid
    for block in new['mainline_reading']['blocks']:
        for part in block['parts']:
            for pointer in part['source_pointers']:
                at(new, pointer)
                pointers += 1
    for record in new['batch_coverage']['records']:
        if record.get('text_duplicate_of', '').startswith('/'):
            at(new, record['text_duplicate_of'])
    joined = [g for g in new.get('task_local_sequences', [])
              if g.get('order_scope') == 'condition_completion_via_information_board']
    if joined:
        consumed = {key for g in joined for key in g['state_keys']}
        old_others = [g['state_keys'] for g in old['task_local_sequences'] if not consumed.intersection(g['state_keys'])]
        new_others = [g['state_keys'] for g in new['task_local_sequences'] if not consumed.intersection(g['state_keys'])]
        assert old_others == new_others, (qid, 'other groups reordered')
        for group in joined:
            assert not group['mainline_placement_verified']
            assert not group['proof']['panel_close_timing_verified']
            for item in group['intermediate_content']:
                assert item['before_segment_index'] == 1
                assert not item['panel_close_timing_verified']
                for event in item['events']:
                    assert event['state_key'] is None
                    assert any(entry.get('source_action') == item['source_action'] and
                               entry.get('information_board') == event['information_board']
                               for entry in old['external_content']), (qid, 'panel source changed')
        changes.append({'quest_id': qid, 'title': task['title'], 'type_id': task['type_id'],
                        'old_text_events': old['mainline_reading']['retained_text_events'],
                        'new_text_events': new['mainline_reading']['retained_text_events'],
                        'groups': [{'node_id': g['node_id'], 'state_keys': g['state_keys'],
                                    'board_ids': [e['information_board']['board_id']
                                                 for c in g['intermediate_content'] for e in c['events']]}
                                   for g in joined]})
    else:
        assert (baseline / old_tasks[qid]['files'][1]).read_bytes() == (current / task['files'][1]).read_bytes(), qid
        unchanged_txt += 1
assert any(c['quest_id'] == 880000025 for c in changes)
result = {'pairs_checked': len(after['tasks']), 'source_pointers_checked': pointers,
          'unchanged_txt_files': unchanged_txt, 'database_hashes_equal': True,
          'original_flow_events_choices_and_external_content_preserved': True,
          'unrelated_local_groups_preserved': True, 'reading_statuses_unchanged': True,
          'changes': changes}
(current / '心愿纸条顺序核对.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
