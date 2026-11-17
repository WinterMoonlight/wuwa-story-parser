"""Verify display-template changes against an existing reading batch."""
import argparse
import json
from pathlib import Path
import re

from wuwa_story.reading import reading_text


PATTERN = re.compile(r'\{(?:\d+|Cus:)[^{}]*\}')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify(baseline, batch):
    before, after = load(baseline / '覆盖报告.json'), load(batch / '覆盖报告.json')
    old_tasks = {t['quest_id']: t for t in before['tasks']}
    assert before['source_sha256'] == after['source_sha256']
    assert before['summary'] == after['summary']
    changed = []
    for task in after['tasks']:
        qid = task['quest_id']
        old_task = old_tasks[qid]
        old, new = load(baseline / old_task['files'][0]), load(batch / task['files'][0])
        for field in ('source', 'events', 'route', 'recap_backbone'):
            assert old.get(field) == new.get(field), (qid, field)
        assert old['batch_coverage']['records'] == new['batch_coverage']['records'], qid
        text = (batch / task['files'][1]).read_text(encoding='utf-8-sig')
        old_text = (baseline / old_task['files'][1]).read_text(encoding='utf-8-sig')
        assert text == reading_text(new), qid
        assert not PATTERN.search(text), qid
        assert len(text.splitlines()) == len(old_text.splitlines()), qid
        if text != old_text:
            samples = [{'line': number, 'before': a, 'after': b}
                       for number, (a, b) in enumerate(zip(old_text.splitlines(), text.splitlines()), 1)
                       if a != b]
            changed.append({'quest_id': qid, 'title': task['title'], 'samples': samples})
    result = {'baseline': str(baseline), 'batch': str(batch), 'pairs_checked': len(after['tasks']),
              'source_and_event_order_preserved': True, 'all_text_records_preserved': True,
              'changed_txt_files': len(changed), 'remaining_supported_template_tokens': 0,
              'reading_policy': 'Guide action labels; selected global string labels within one task; descriptive fallback for unknown values',
              'changes': changed}
    (batch / '占位符核对.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (batch / '产物核对.json').write_text(json.dumps({k: v for k, v in result.items() if k != 'changes'},
                                                 ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'changes'}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('batch', type=Path)
    args = parser.parse_args()
    verify(args.baseline, args.batch)
