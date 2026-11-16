"""Caption text extraction with conservative consensus ordering of numeric tracks."""
import base64
import hashlib
import struct
from .database import field, integer, string, texts
from .rendering import render_text


def decode_captions(name, rows):
    decoded = []
    for row in rows:
        blob = row['BinData']
        root = struct.unpack_from('<I', blob)[0]
        vt = root - struct.unpack_from('<i', blob, root)[0]
        if struct.unpack_from('<H', blob, vt)[0] != 26:
            raise ValueError('Unknown caption field layout')
        if integer(blob, 0) != row['CaptionId'] or string(blob, 1) != name:
            raise ValueError('Caption row identity mismatch')
        key = string(blob, 4)
        if not key:
            raise ValueError('Missing caption text reference')
        tracks = [[integer(blob, a), integer(blob, b)] for a, b in [(2, 3), (5, 6), (7, 8), (9, 10)]]
        decoded.append({'caption_id': row['CaptionId'], 'text_id': key,
                        'raw_text': texts.get(key), 'text': render_text(texts[key]) if key in texts else '[缺失字幕正文]',
                        'missing': key not in texts, 'display_name': '字幕', 'kind': 'subtitle',
                        'numeric_tracks': tracks,
                        'sha256': hashlib.sha256(blob).hexdigest(),
                        'bin_data_base64': base64.b64encode(blob).decode('ascii')})
    if len({r['caption_id'] for r in decoded}) != len(decoded):
        raise ValueError('Duplicate caption IDs')
    orders = []
    for track in range(4):
        values = [r['numeric_tracks'][track] for r in decoded]
        if any(a < 0 or b <= 0 for a, b in values) or len({a for a, _ in values}) != len(values):
            orders.append(None)
        else:
            orders.append([r['caption_id'] for r in sorted(decoded, key=lambda r: r['numeric_tracks'][track][0])])
    agreed = bool(decoded) and orders[0] is not None and all(order == orders[0] for order in orders)
    if agreed:
        indexed = {r['caption_id']: r for r in decoded}
        decoded = [indexed[i] for i in orders[0]]
    return {'captions': decoded, 'caption_order_consensus': agreed,
            'caption_order_evidence': {'candidate_orders': orders,
                'basis': 'Agreement of four numeric start-position tracks; inferred relative order only',
                'track_language_mapping_verified': False, 'time_unit_verified': False,
                'runtime_playback_verified': False},
            'caption_missing_text_ids': [r['text_id'] for r in decoded if r['missing']]}
