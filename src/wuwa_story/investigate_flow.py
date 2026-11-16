"""Read-only evidence for a flow family; does not rewrite references.

python -m wuwa_story.investigate_flow FLOW_LIST FLOW_ID TEXT_ID OUTPUT.json
"""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from .database import P, rows, embedded, texts, vec
from .export_task import flow_actions, walk
from .reference_diagnostics import audio_index
from .audit_missing import quote


def paths(value, path=()):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from paths(child, path + (key,))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from paths(child, path + (i,))


def investigate(name, flow_id, text_id):
    owners, scanned = [], []
    needles = [name.encode(), json.dumps(name)[1:-1].encode()]
    for file in sorted(P.glob('*.db')):
        scanned.append({'file': file.name, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
        with sqlite3.connect(file.as_uri() + '?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            for (table,) in tables:
                for row in db.execute('SELECT * FROM ' + quote(table)):
                    for col, blob in dict(row).items():
                        if not isinstance(blob, bytes) or not any(n in blob for n in needles):
                            continue
                        for field, value in embedded(blob):
                            for path, obj in paths(value):
                                if obj.get('FlowListName') == name and obj.get('FlowId') == flow_id:
                                    owners.append({'file': file.name, 'table': table,
                                                   'row': {k: v for k, v in dict(row).items() if not isinstance(v, bytes)},
                                                   'blob_column': col, 'json_field': field, 'path': list(path),
                                                   'reference': obj, 'source_json': value,
                                                   'blob_sha256': hashlib.sha256(blob).hexdigest()})
    by_id, by_event = audio_index(rows)
    event = by_id.get(text_id, {}).get('audio_event')
    candidates = by_event.get(event, [])
    candidate_keys = {x['text_id'] for x in candidates}
    states = []
    for row in rows('db_flowState.db', 'flowstate'):
        try:
            actions, _ = flow_actions(row['BinData'])
        except ValueError:
            continue
        if row['StateKey'].startswith(f'{name}_{flow_id}_') or any(o.get('TidTalk') in candidate_keys for o in walk(actions)):
            states.append({'state_key': row['StateKey'], 'actions': actions,
                           'sha256': hashlib.sha256(row['BinData']).hexdigest(),
                           'texts': {o['TidTalk']: texts.get(o['TidTalk']) for o in walk(actions) if o.get('TidTalk')}})
    conflicting = [{'event': event, 'entries': [dict(e, text=texts.get(e['text_id'])) for e in entries]}
                   for event, entries in by_event.items()
                   if len({texts[e['text_id']] for e in entries if texts.get(e['text_id'])}) > 1]
    catalog = []
    for row in rows('db_flow.db', 'flow'):
        if row['Id'] == f'{name}_{flow_id}':
            catalog.append({'id': row['Id'], 'field_1_int_vector': vec(row['BinData'], 1),
                            'field_2_int_vector': vec(row['BinData'], 2),
                            'sha256': hashlib.sha256(row['BinData']).hexdigest()})
    return {'scope': 'Root SQLite BLOBs containing UTF-8/JSON-escaped flow list, decodable embedded JSON references; not all binary fields or runtime assets',
            'flow_list': name, 'flow_id': flow_id, 'text_id': text_id,
            'owners': owners, 'states': states, 'catalog': catalog,
            'shared_audio_candidates': candidates,
            'shared_audio_conflict_count': len(conflicting), 'shared_audio_conflicts': conflicting,
            'scanned_files': scanned, 'conclusion': 'No verified text replacement; preserve missing text',
            'version_history_checked': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('flow_list')
    parser.add_argument('flow_id', type=int)
    parser.add_argument('text_id')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = investigate(args.flow_list, args.flow_id, args.text_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(len(result['owners']), 'flow references;', result['shared_audio_conflict_count'], 'shared audio conflicts')
