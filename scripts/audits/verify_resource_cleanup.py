"""Compare a cleaned reading batch and refresh exact missing-reference evidence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from wuwa_story.audit_missing import audit
from wuwa_story.database import rows, vec
from wuwa_story.export_task import flow_key
from wuwa_story.reading import reading_text
from wuwa_story.reading_markup import TAG, reading_markup


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def entry_hash(entry):
    return hashlib.sha256(json.dumps(entry, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def neighbor_text(segments, index, step):
    for position in range(index + step, len(segments) if step > 0 else -1, step):
        events = [e for e in segments[position]['events'] if e['kind'] in {'dialogue', 'choice', 'narration'}]
        if events:
            selected = events[:2] if step > 0 else events[-2:]
            return [{'speaker': e.get('display_name'), 'text': e['text']} for e in selected]
    return []


def verify(old, new, review_path):
    before, after = load(old / '覆盖报告.json'), load(new / '覆盖报告.json')
    old_tasks = {t['quest_id']: t for t in before['tasks']}
    assert before['source_sha256'] == after['source_sha256']
    assert before['summary']['status'] == after['summary']['status']
    assert len(old_tasks) == len(after['tasks'])
    state_rows = {r['StateKey']: r for r in rows('db_flowState.db', 'flowstate')}
    flow_rows = {r['Id']: r for r in rows('db_flow.db', 'flow')}
    user_review = load(review_path)
    changed, unexplained, missing = [], [], []
    removed_tags = Counter()
    for task in after['tasks']:
        qid = task['quest_id']
        prior = old_tasks[qid]
        a, b = load(old / prior['files'][0]), load(new / task['files'][0])
        assert a['source'] == b['source'], qid
        assert a['route'] == b['route'], qid
        old_segments = (a.get('recap_backbone') or {}).get('segments', [])
        segments = (b.get('recap_backbone') or {}).get('segments', [])
        assert [(s['state_key'], s['source_entry']) for s in old_segments] == [
            (s['state_key'], s['source_entry']) for s in segments], qid
        # Both selected events and per-segment events retain their order and source.
        for first, second in [(a['events'], b['events']), *zip(
                [s['events'] for s in old_segments], [s['events'] for s in segments])]:
            assert [(e.get('state_key'), e.get('talk_id'), e.get('text_id'), e.get('source_item')) for e in first] == [
                (e.get('state_key'), e.get('talk_id'), e.get('text_id'), e.get('source_item')) for e in second], qid
        old_text = (old / prior['files'][1]).read_text(encoding='utf-8-sig')
        new_text = (new / task['files'][1]).read_text(encoding='utf-8-sig')
        assert new_text == reading_text(b), qid
        assert not TAG.search(new_text), qid
        removed_tags[qid] = len(TAG.findall(old_text))
        if old_text != new_text:
            changed.append(qid)
        if reading_markup(old_text) != new_text:
            unexplained.append(qid)
        for i, segment in enumerate(segments):
            if segment.get('error') != 'Missing flow state':
                continue
            key = segment['state_key']
            assert key not in state_rows
            family = flow_key(segment['source_entry']['Flow']).rsplit('_', 1)[0]
            catalog = flow_rows.get(family)
            vectors = []
            if catalog:
                for field in (1, 2):
                    try:
                        vectors.append({'field': field, 'values': vec(catalog['BinData'], field)})
                    except (ValueError, struct.error) as exc:
                        vectors.append({'field': field, 'decoding_error': type(exc).__name__})
            item = {'quest_id': qid, 'title': task['title'], 'files': task['files'],
                    'entry_index': segment['entry_index'], 'state_key': key,
                    'source_entry': segment['source_entry'],
                    'source_entry_sha256': entry_hash(segment['source_entry']),
                    'status': 'unresolved_flow_definition',
                    'available_family_states': sorted(k for k in state_rows if k.startswith(family + '_')),
                    'catalog_exists': catalog is not None,
                    'catalog_vector_candidates': vectors,
                    'before': neighbor_text(segments, i, -1), 'after': neighbor_text(segments, i, 1),
                    'replacement_applied': False}
            if all(item.get(k) == user_review.get(k) for k in ('quest_id', 'state_key', 'source_entry_sha256')):
                item.update(status=user_review['status'], user_review=user_review)
            missing.append(item)
    text_evidence = audit(new / '覆盖报告.json')
    assert all(not t['unlocated_report_keys'] for t in text_evidence['tasks'])
    # The only semantic TXT change is removal of a false missing-text footer.
    assert set(unexplained) <= {125000129}, unexplained
    report = {'baseline': str(old), 'batch': str(new), 'pairs_checked': len(after['tasks']),
              'source_data_and_selected_event_order_preserved': True,
              'changed_txt_tasks': changed, 'tagged_txt_tasks': sum(bool(n) for n in removed_tags.values()),
              'removed_tag_count': sum(removed_tags.values()), 'remaining_tags': 0,
              'other_txt_changes': unexplained,
              'missing_flow_occurrences': missing, 'missing_text_evidence': text_evidence,
              'summary': {'unique_missing_flows': len({m['state_key'] for m in missing}),
                          'missing_flow_occurrences': len(missing),
                          'missing_flow_tasks': len({m['quest_id'] for m in missing}),
                          'user_reported_cutscene_occurrences': sum(m['status'] == 'user_reported_cutscene' for m in missing),
                          'remaining_body_keys': text_evidence['unique_keys']}}
    (new / '资源引用与标签核对.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 资源引用与标签核对', '',
             f'核对{len(after["tasks"])}对JSON/TXT，来源、所选事件顺序和原始回顾条目保持。',
             f'清理{report["tagged_txt_tasks"]}份TXT中的{report["removed_tag_count"]}个残留标签，当前匹配到的残留标签为0。',
             '《我们选择天空》的两条表情和一个图片附件已按媒体引用处理，移除正文缺失误报。', '',
             '## 缺失流程逐处上下文', '',
             '以下编号来自回顾配置。前后台词取自最近的已提取段落，连续空引用会共用同一段上下文。候选状态与缺失状态的对应关系仍待确认。', '']
    for item in missing:
        lines += [f'### {item["quest_id"]} {item["title"]}，回顾条目{item["entry_index"]}', '',
                  f'- 文件 [TXT](<{item["files"][1]}>)。',
                  f'- 引用 `{item["state_key"]}`。',
                  '- 用户反馈此处为过程动画，原始流程定义仍未找到。' if item['status'] == 'user_reported_cutscene'
                  else '- 当前状态为定义未找到，是否遗漏可读对白尚无定论。', '', '前方最近已提取段落的结尾', '']
        lines += [f'> {e["speaker"] or "无署名"}：{reading_markup(e["text"])}' for e in item['before']] or ['无已提取对白。']
        lines += ['', '后方最近已提取段落的开头', '']
        lines += [f'> {e["speaker"] or "无署名"}：{reading_markup(e["text"])}' for e in item['after']] or ['无已提取对白。']
        lines.append('')
    lines += ['## 剩余正文引用', '',
              '《灼我以烈阳》的Main_Linaxita_2_9_605_1仍未找到正文。已复查473个语言及子目录数据库，精确键命中为0。',
              '共用语音对应“这个声音是……”仅作为候选记录，当前缺少明确的文字替换关系。', '',
              '## 核查边界', '',
              '此次复查读取当前flowState、flow目录与导出的回顾条目，并重查语言数据库。媒体内部、历史版本和运行时生成内容尚未核验。', '']
    (new / '资源引用与标签核对.md').write_text('\n'.join(lines), encoding='utf-8')
    (new / '产物核对.json').write_text(json.dumps({k: report[k] for k in (
        'baseline', 'batch', 'pairs_checked', 'source_data_and_selected_event_order_preserved',
        'changed_txt_tasks', 'tagged_txt_tasks', 'removed_tag_count', 'remaining_tags', 'other_txt_changes')},
        ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False))
    print('Changed TXT', len(changed), 'cleaned tags', report['removed_tag_count'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('batch', type=Path)
    parser.add_argument('--review', type=Path, default=Path('docs/reviews/user-resource-145000005.json'))
    args = parser.parse_args()
    verify(args.baseline, args.batch, args.review)
