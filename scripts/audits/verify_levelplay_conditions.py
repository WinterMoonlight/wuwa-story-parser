"""Check that newly inventoried completion flows preserve existing story output."""
import argparse
from collections import Counter
import json
from pathlib import Path

from wuwa_story.reading import reading_text


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def record_key(record):
    return record.get('origin'), record.get('text_id'), record.get('text')


def verify(baseline, batch):
    old_report, report = load(baseline / '覆盖报告.json'), load(batch / '覆盖报告.json')
    old_tasks = {t['quest_id']: t for t in old_report['tasks']}
    assert len(old_tasks) == len(report['tasks'])
    assert old_report['source_sha256'] == report['source_sha256']
    assert old_report['summary']['status'] == report['summary']['status']
    changed = []
    for task in report['tasks']:
        qid = task['quest_id']
        previous = old_tasks[qid]
        old, current = load(baseline / previous['files'][0]), load(batch / task['files'][0])
        for field in ('source', 'events', 'route', 'recap_backbone'):
            assert old.get(field) == current.get(field), (qid, field)
        old_records = Counter(record_key(r) for r in old['batch_coverage']['records'])
        records = Counter(record_key(r) for r in current['batch_coverage']['records'])
        assert not old_records - records, qid
        added = records - old_records
        condition_keys = {link['state_key'] for link in current['batch_coverage']['declared_levelplay_links']
                          if link['phase'] == 'Condition'}
        assert all(key[0] in condition_keys for key in added), qid
        for record in current['batch_coverage']['records']:
            if record_key(record) in added:
                assert record['reading_context'] == 'declared_levelplay_candidate', qid
                assert record['category'] == 'candidate_branch', qid
                assert record['order_verified'] is False, qid
        txt = (batch / task['files'][1]).read_text(encoding='utf-8-sig')
        assert txt == reading_text(current), qid
        if txt != (baseline / previous['files'][1]).read_text(encoding='utf-8-sig'):
            changed.append({'quest_id': qid, 'title': task['title'],
                            'added_candidate_records': sum(added.values()), 'files': task['files']})
    result = {'baseline': str(baseline), 'batch': str(batch), 'pairs_checked': len(report['tasks']),
              'source_data_preserved': True, 'existing_routes_and_recap_segments_preserved': True,
              'all_previous_text_records_preserved': True, 'new_records_are_unordered_candidates': True,
              'changed_txt_tasks': changed,
              'added_candidate_records': sum(t['added_candidate_records'] for t in changed)}
    (batch / '产物核对.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('batch', type=Path)
    args = parser.parse_args()
    verify(args.baseline, args.batch)
