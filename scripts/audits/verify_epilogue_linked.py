import json
import sys
from pathlib import Path
from collections import Counter

from wuwa_story.mainline_reading import build_mainline_reading, mainline_reading_text


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def at(document, pointer):
    value = document
    for key in pointer.strip('/').split('/'):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


baseline, current = map(Path, sys.argv[1:])
before, after = (load(root / '覆盖报告.json') for root in (baseline, current))
assert before['source_sha256'] == after['source_sha256']
previous = {t['quest_id']: t for t in before['tasks']}
assert set(previous) == {t['quest_id'] for t in after['tasks']}
changes, pointers, unchanged = [], 0, 0
for task in after['tasks']:
    qid = task['quest_id']
    old = load(baseline / previous[qid]['files'][0])
    new = load(current / task['files'][0])
    for field in ('source', 'events', 'route', 'external_content', 'recap_backbone', 'task_local_sequences'):
        assert old.get(field) == new.get(field), (qid, field)
    view = build_mainline_reading(new)
    assert new['mainline_reading'] == view, qid
    text = (current / task['files'][1]).read_text(encoding='utf-8-sig')
    assert text == mainline_reading_text(new), qid
    for block in view['blocks']:
        for part in block['parts']:
            for pointer in part['source_pointers']:
                at(new, pointer)
                pointers += 1
    sections = new.get('linked_recap_sections', [])
    if sections:
        originals = {entry['unplaced_flow']['state_key']: entry
                     for entry in old['external_content'] if 'unplaced_flow' in entry}
        segment_keys = []
        for section in sections:
            assert not section['runtime_verified']
            assert not section['proof']['runtime_node_order_verified']
            for segment in section['segments']:
                segment_keys.append(segment['state_key'])
                source_events = [x['source_event'] for x in originals[segment['state_key']]['texts']]
                source_ids = Counter((e.get('text_id'), e['raw_text']) for e in source_events)
                current_ids = Counter((e.get('text_id'), e['raw_text']) for e in segment['events'])
                assert source_ids == current_ids, (qid, segment['state_key'], 'changed selected text')
        assert len(segment_keys) == len(set(segment_keys))
        assert new['validation']['reading_unplaced_flow_count'] == 0
        assert not new['validation']['complete_for_supported_task_shape']
        assert not new['batch_coverage']['order']['selected_route_verified']
        assert new['batch_coverage']['strict_pass'] == old['batch_coverage']['strict_pass']
        changes.append({'quest_id': qid, 'title': task['title'],
                        'old_text_events': old['mainline_reading']['retained_text_events'],
                        'new_text_events': view['retained_text_events'],
                        'old_status': old['mainline_reading']['status'], 'new_status': view['status'],
                        'recovered_state_keys': segment_keys,
                        'source_quest_ids': [section['source_quest_id'] for section in sections]})
    else:
        assert old['mainline_reading'] == view, qid
        assert (baseline / previous[qid]['files'][1]).read_bytes() == (current / task['files'][1]).read_bytes(), qid
        unchanged += 1
assert [item['quest_id'] for item in changes] == [168850009]
result = {'pairs_checked': len(after['tasks']), 'unchanged_txt_files': unchanged,
          'reading_source_pointers_checked': pointers, 'database_hashes_equal': True,
          'original_primary_events_choices_and_source_material_preserved': True,
          'linked_flow_selected_text_matches_original_supplements': True,
          'strict_validation_not_promoted': True, 'changes': changes}
(current / '后日谈关联回顾核对.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
