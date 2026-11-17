import json
import sys
from collections import Counter
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
    old_segments, new_segments = segments(old), segments(new)
    assert old_segments.keys() <= new_segments.keys(), (qid, 'lost segment')
    for key, segment in old_segments.items():
        assert segment == new_segments[key], (qid, key, 'changed original events/choices')
    previous_groups = [g['state_keys'] for g in old.get('task_local_sequences', [])]
    retained_groups = [g['state_keys'] for g in new.get('task_local_sequences', [])
                       if all(k in old_segments for k in g['state_keys'])]
    assert retained_groups == previous_groups, (qid, 'changed old local ordering')
    assert new['mainline_reading']['status'] == old['mainline_reading']['status'], (qid, 'status promotion')
    assert new['mainline_reading'] == build_mainline_reading(new), qid
    assert (current / task['files'][1]).read_text(encoding='utf-8-sig') == mainline_reading_text(new), qid
    for block in new['mainline_reading']['blocks']:
        for part in block['parts']:
            for pointer in part['source_pointers']:
                at(new, pointer)
                pointers += 1
    added = set(new_segments) - set(old_segments)
    if added:
        groups = [g for g in new['task_local_sequences'] if any(k in added for k in g['state_keys'])]
        assert all(not g['mainline_placement_verified'] for g in groups), qid
        changes.append({'quest_id': qid, 'title': task['title'], 'type_id': task['type_id'],
                        'added_state_keys': sorted(added),
                        'old_text_events': old['mainline_reading']['retained_text_events'],
                        'new_text_events': new['mainline_reading']['retained_text_events']})
    else:
        assert (baseline / old_tasks[qid]['files'][1]).read_bytes() == (current / task['files'][1]).read_bytes(), qid
        unchanged_txt += 1
    for relation in new.get('sequence_dependency_review', {}).get('flow_progression', {}).get('phase_relations', []):
        assert relation['from_call']['node_id'] == relation['to_call']['node_id'], qid
        assert not relation['whole_task_order_verified'], qid
        if relation['from_call']['invocation_async']:
            assert not relation['flow_completion_before_followup_verified'], qid
assert next(c for c in changes if c['quest_id'] == 125000121)['new_text_events'] == 186
result = {'pairs_checked': len(after['tasks']), 'source_pointers_checked': pointers,
          'unchanged_txt_files': unchanged_txt, 'database_hashes_equal': True,
          'original_segments_and_local_order_preserved': True,
          'original_mainline_and_choices_preserved': True, 'reading_statuses_unchanged': True,
          'changes': changes}
(current / '多阶段调用核对.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
