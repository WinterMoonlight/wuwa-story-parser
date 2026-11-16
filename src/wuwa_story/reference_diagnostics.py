"""Missing text evidence. Shared audio is a candidate link, not a text alias."""
from collections import defaultdict
import hashlib
import struct

from .database import string, texts


def audio_index(read_rows):
    by_id, by_event = {}, defaultdict(list)
    for row in read_rows('db_plot_audio.db', 'plotaudio'):
        blob = row['BinData']
        try:
            key, event = string(blob, 0), string(blob, 2)
        except (ValueError, UnicodeError, struct.error):
            continue
        if key != row['Id'] or not event:
            continue
        entry = {'text_id': key, 'audio_event': event,
                 'source_sha256': hashlib.sha256(blob).hexdigest()}
        by_id[key] = entry
        by_event[event].append(entry)
    return by_id, by_event


def diagnose_missing(records, task_refs, recap_refs, read_rows):
    missing = [r for r in records if r.get('missing') and r.get('origin')]
    if not missing:
        return []
    by_id, by_event = audio_index(read_rows)
    out = []
    for record in missing:
        key, state = record['text_id'], record['origin']
        audio = by_id.get(key)
        candidates = [dict(entry, raw_text=texts[entry['text_id']])
                      for entry in by_event.get(audio['audio_event'], [])
                      if entry['text_id'] != key and texts.get(entry['text_id'])] if audio else []
        out.append({'text_id': key, 'state_key': state, 'source_path': record['source_path'],
                    'task_referenced': state in task_refs, 'recap_referenced': state in recap_refs,
                    'status': 'unresolved_body_reference', 'audio_source': audio,
                    'shared_audio_candidates': candidates, 'replacement_applied': False,
                    'reason': 'Shared audio does not prove identical subtitles or a replacement mapping'})
    return out
