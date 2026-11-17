"""Check the concise reading projection against the preceding evidence batch."""
import argparse
import json
from pathlib import Path

from wuwa_story.mainline_reading import (
    STORY_KINDS, build_mainline_reading, mainline_reading_text, write_mainline_report,
)


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def resolve(document, pointer):
    value = document
    for key in pointer.strip('/').split('/'):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def verify(baseline, batch):
    old_report = load(baseline / '覆盖报告.json')
    report = load(batch / '覆盖报告.json')
    old_tasks = {task['quest_id']: task for task in old_report['tasks']}
    assert old_report['source_sha256'] == report['source_sha256']
    assert old_report['summary'] == report['summary']
    checked = 0
    pointers = 0
    for task in report['tasks']:
        document = load(batch / task['files'][0])
        old = load(baseline / old_tasks[task['quest_id']]['files'][0])
        old.pop('mainline_reading', None)
        original = {key: value for key, value in document.items() if key != 'mainline_reading'}
        assert original == old, (task['quest_id'], 'source evidence changed')
        view = document['mainline_reading']
        assert view == build_mainline_reading(document), task['quest_id']
        text = (batch / task['files'][1]).read_text(encoding='utf-8-sig')
        assert text == mainline_reading_text(document), task['quest_id']
        for token in ('【补充片段】', '【小游戏·第', '【卡牌文本】'):
            assert token not in text, (task['quest_id'], token)
        retained = set()
        for block in view['blocks']:
            for part in block['parts']:
                for pointer in part['source_pointers']:
                    resolve(document, pointer)
                    retained.add(pointer)
                    pointers += 1
        sources = []
        if document.get('recap_backbone'):
            for index, segment in enumerate(document['recap_backbone']['segments']):
                if segment['status'] != 'excluded_branch':
                    sources.append((f'/recap_backbone/segments/{index}/events', segment['events']))
        else:
            sources.append(('/events', document['events']))
        for source_pointer, events in sources:
            ordered_pointers = [source_pointer + '/' + str(index) for index, event in enumerate(events)
                                if event.get('kind') in STORY_KINDS]
            actual = [pointer for block in view['blocks'] for part in block['parts']
                      for pointer in part['source_pointers'] if pointer in ordered_pointers]
            assert actual == ordered_pointers, (task['quest_id'], source_pointer)
        checked += 1
    reading_report = write_mainline_report(batch, report['tasks'])
    result = {'pairs_checked': checked, 'source_pointers_checked': pointers,
              'original_json_evidence_unchanged': True,
              'source_database_hashes_unchanged': True,
              'retained_event_order_verified': True,
              'runtime_order_verified': False,
              'reading_summary': reading_report['summary']}
    (batch / '主线阅读核对.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('batch', type=Path)
    args = parser.parse_args()
    verify(args.baseline, args.batch)
