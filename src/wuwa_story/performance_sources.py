"""Exact asset-to-video links; absence of captions never proves silence."""
import hashlib
from .database import string, WORK_DIR


def sequence_source(asset_path, read_rows):
    matches = []
    for row in read_rows('db_cgVedio.db', 'videodata'):
        if string(row['BinData'], 4) == asset_path:
            matches.append({'cg_id': row['CgId'], 'video_name': row['CgName'],
                            'gender_code': row['GirlOrBoy'],
                            'sha256': hashlib.sha256(row['BinData']).hexdigest()})
    package, _, name = asset_path.rpartition('.')
    safe = name and '/' not in name and '\\' not in name
    path = WORK_DIR / 'asset_exports' / 'properties' / (name + '.json') if safe else None
    evidence = {'asset_path': asset_path, 'match_rule': 'exact_videodata_asset_path',
                'video_matches': matches, 'asset_content_decoded': False,
                'properties_status': 'available_unparsed' if path and path.is_file() else 'not_available',
                'expected_properties_file': 'work/asset_exports/properties/' + name + '.json' if safe else None,
                'fmodel_package': package if package else asset_path,
                'text_status': 'source_unresolved', 'silence_verified': False}
    if path and path.is_file():
        evidence['properties_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    if len(matches) == 1 and matches[0]['gender_code'] == 0:
        from .external import inspect_movie
        media = inspect_movie(matches[0]['video_name'], read_rows)
        if media['asset_path'] == asset_path:
            evidence.update(text_status=media['text_coverage'], media=media)
    return evidence
