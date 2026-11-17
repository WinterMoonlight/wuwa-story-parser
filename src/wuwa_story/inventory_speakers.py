"""Attribute static text without borrowing an ancestor's actor or executing branches."""
from .rendering import render_text


def option_context(parent):
    kind = parent.get('Type')
    if kind == 'QTE':
        return 'qte_result'
    if kind == 'SystemOption':
        return 'system_option'
    if kind in {'Talk', 'Option', 'VisualNovelTalk', 'VisualNovelNarration',
                'VisualNovelOption', 'AvgTalk', 'AvgNarration', 'PhoneMessage'}:
        return 'choice'
    if kind is None and 'Id' in parent and ('TidTalk' in parent or 'TextId' in parent):
        return 'choice'
    return 'unknown_option'


def inventory_identity(key, item, speakers, context):
    if key == 'TidCenterText':
        return {'kind': 'screen_text', 'who_id': None, 'display_name': '画面文字',
                'identity_status': 'not_applicable', 'attribution_basis': 'TidCenterText'}
    if key == 'TidTalkOption':
        kind = context or 'unknown_option'
        name = {'choice': '漂泊者', 'qte_result': 'QTE结果文字',
                'system_option': '系统选项'}.get(kind, '？？？')
        return {'kind': kind, 'who_id': None, 'display_name': name,
                'identity_status': 'player_option' if kind == 'choice' else 'not_speech_verified',
                'attribution_basis': {'field': key, 'option_context': context},
                'selected': False}
    sid = item.get('WhoId')
    # Static inventory cannot replay actor changes, so use only the name table.
    record = speakers.records.get(sid, {'name': '', 'source': 'unresolved'})
    if record.get('configured_empty_name') is True:
        return {'kind': 'dialogue', 'who_id': sid, 'speaker_id': sid,
                'display_name': '无署名', 'name_source': dict(record),
                'identity_status': 'configured_empty_name',
                'attribution_basis': 'own_WhoId_configured_empty_name',
                'resolved_speaker_id': None, 'resolved_name': None}
    name = render_text(record.get('name') or '？？？')
    unknown = not name.strip() or set(name.strip()) <= {'?', '？'}
    return {'kind': 'dialogue', 'who_id': sid, 'speaker_id': sid,
            'display_name': name if name.strip() else '？？？', 'name_source': dict(record),
            'identity_status': 'unresolved' if unknown else 'display_name_only',
            'attribution_basis': 'own_WhoId_only',
            'resolved_speaker_id': None, 'resolved_name': None}
