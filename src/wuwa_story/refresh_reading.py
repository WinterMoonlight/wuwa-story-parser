"""Refresh existing reading editions without rewriting their JSON evidence."""
import hashlib
import json
from pathlib import Path
from .database import O
from .mainline_reading import build_mainline_reading, mainline_reading_text


def refresh_reading(root=O):
    root = Path(root)
    prepared = []
    for path in sorted(root.rglob('*.json')):
        raw = path.read_bytes()
        data = json.loads(raw.decode('utf-8-sig'))
        if not isinstance(data, dict) or not all(k in data for k in ('quest_id', 'title', 'events', 'validation')):
            continue
        document = {**data, 'mainline_reading': build_mainline_reading(data)}
        text = mainline_reading_text(document)
        prepared.append((path, data, raw, text))
    records = []
    for path, data, raw, text in prepared:
        output = path.with_suffix('.txt')
        changed = not output.exists() or output.read_text(encoding='utf-8-sig') != text
        if changed:
            output.write_text(text, encoding='utf-8-sig')
        if path.read_bytes() != raw:
            raise RuntimeError('JSON evidence changed during refresh: ' + str(path))
        if output.read_text(encoding='utf-8-sig') != text:
            raise RuntimeError('TXT verification failed: ' + str(output))
        records.append({'quest_id': data['quest_id'], 'title': data['title'],
                        'json': path.relative_to(root).as_posix(),
                        'txt': output.relative_to(root).as_posix(), 'txt_changed': changed,
                        'json_sha256': hashlib.sha256(raw).hexdigest(), 'json_unchanged': True})
    report = {'task_files': len(records), 'unique_tasks': len({r['quest_id'] for r in records}),
              'txt_changed': sum(r['txt_changed'] for r in records), 'records': records}
    (root / '阅读版更新清单.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 已导出任务阅读索引', '', 'TXT 为阅读版，完整技术记录保存在同名 JSON。历史批次沿用各自原有路线和证据。', '',
             'TXT保留主干和简短过程说明，复杂玩法和候选分支保存在JSON；局部片段会标明顺序范围。', '', '## 任务入口', '']
    for qid in sorted({r['quest_id'] for r in records}):
        candidates = [r for r in records if r['quest_id'] == qid]
        chosen = min(candidates, key=lambda r: (len(Path(r['txt']).parts), r['txt']))
        lines.append(f"- {chosen['title']}：[TXT](<{chosen['txt']}>) · [JSON](<{chosen['json']}>)")
    lines += ['', f"共 {report['unique_tasks']} 个任务、{report['task_files']} 份导出；全部 JSON 已确认未改写。"]
    (root / '阅读版索引.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print({k: v for k, v in report.items() if k != 'records'})
    return report
