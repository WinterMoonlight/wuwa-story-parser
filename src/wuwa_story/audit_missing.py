"""Audit a previous coverage report against the current local language snapshot.

Usage: python -m wuwa_story.audit_missing REPORT.json OUTPUT.json
Scans exact string values, not guessed numeric TextId joins or translated prose.
"""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from .database import P, rows, texts
from .export_task import flow_actions
from .text_refs import non_dialogue_reason, phone_media_reference


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def audit(report_path):
    report = json.loads(report_path.read_text(encoding='utf-8'))
    states = {r['StateKey']: r for r in rows('db_flowState.db', 'flowstate')}
    tasks, keys = [], set()
    for task in report['tasks']:
        if not any(g['kind'] == 'missing_text' for g in task['gaps']):
            continue
        result = json.loads((report_path.parent / task['files'][0]).read_text(encoding='utf-8'))
        recap_only = {key for gap in task['gaps'] if gap['kind'] == 'recap_reference_difference'
                      for key in gap.get('recap_only', [])}
        reported = {k for g in task['gaps'] if g['kind'] == 'missing_text' for k in g['text_ids']}
        refs = []
        for record in result['batch_coverage']['records']:
            value = result
            if record.get('pointer'):
                for part in record['pointer'].strip('/').split('/'):
                    value = value[int(part)] if isinstance(value, list) else value[part]
            else:
                value = record
            key = value.get('text_id')
            if key not in reported:
                continue
            keys.add(key)
            state_key = value.get('state_key') or record.get('origin')
            row = states[state_key]
            node = value.get('source_item')
            if node is None:
                node = flow_actions(row['BinData'])[0]
                for part in record['source_path'][:-1]:
                    node = node[part]
            reason = non_dialogue_reason(node)
            visual = phone_media_reference(node)
            classification = ('media_reference' if visual else
                              'control_reference' if reason else 'unresolved_body_reference')
            refs.append({'text_id': key, 'state_key': state_key,
                         'reference_scope': 'recap_only' if state_key in recap_only else 'task_or_shared',
                         'source_path': record.get('source_path'), 'pointer': record.get('pointer'),
                         'source_item': node,
                         'source_sha256': hashlib.sha256(row['BinData']).hexdigest(),
                         'classification': classification,
                         'reason': reason or ('phone_visual' if visual else
                             'Ordinary speech reference; missing resource versus stale/wrong reference not proven')})
        observed = {r['text_id'] for r in refs}
        tasks.append({'quest_id': task['quest_id'], 'title': task['title'], 'references': refs,
                      'unlocated_report_keys': sorted(reported - observed)})
        keys.update(reported)
    hits, files = [], []
    if keys:
        for path in sorted(P.rglob('*.db')):
            # Language directories; root config blobs are not language text tables.
            if path.parent == P:
                continue
            count = 0
            with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
                tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                for (table,) in tables:
                    for column in db.execute('PRAGMA table_info(' + quote(table) + ')').fetchall():
                        if 'TEXT' not in column[2].upper():
                            continue
                        count += 1
                        sql = ('SELECT * FROM ' + quote(table) + ' WHERE ' + quote(column[1])
                               + ' IN (' + ','.join('?' for _ in keys) + ')')
                        cursor = db.execute(sql, sorted(keys))
                        names = [d[0] for d in cursor.description]
                        for row in cursor:
                            hits.append({'file': path.relative_to(P).as_posix(), 'table': table,
                                         'column': column[1],
                                         'row': {n: (v.hex() if isinstance(v, bytes) else v) for n, v in zip(names, row)}})
            files.append({'file': path.relative_to(P).as_posix(), 'text_columns_checked': count,
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    return {'scope': 'Exact values in declared TEXT columns of all local language/subdirectory databases; no external/asset search',
            'source_report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
            'unique_keys': sorted(keys), 'tasks': tasks, 'language_hits': hits, 'scanned_files': files,
            'current_multi_text_presence': {k: k in texts for k in sorted(keys)}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = audit(args.report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"{len(result['tasks'])} tasks, {len(result['unique_keys'])} keys, "
          f"{len(result['language_hits'])} language hits, {len(result['scanned_files'])} databases")
