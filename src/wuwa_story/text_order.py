"""Report known-text order separately from missing data and media coverage."""
from collections import Counter
from copy import deepcopy
import json

from .terminal_text import synchronous


def deferred_sequence(actions, key):
    """An isolated final media call carries no local dialogue to order."""
    if (not actions or any(not synchronous(a, 'SetPlotMode') for a in actions[:-1])
            or not synchronous(actions[-1], 'PlaySequenceData')):
        return None
    call = actions[-1]
    params = call.get('Params', {})
    from .sequence_calls import sequence_call
    # Existing accepted calls may already carry decoded subtitles. Preserve
    # their normal path and apply deferral only to newly admitted callbacks.
    if sequence_call(params):
        return None
    if (not isinstance(params, dict) or set(params) - {'Path', 'ResetCamera', 'FrameEvents'}
            or not isinstance(params.get('Path'), str) or not params['Path']
            or ('ResetCamera' in params and type(params['ResetCamera']) is not bool)):
        return None
    frames = params.get('FrameEvents', [])
    if not isinstance(frames, list):
        return None
    keys = []
    for frame in frames:
        if (not isinstance(frame, dict) or set(frame) != {'EventKey', 'EventActions'}
                or not isinstance(frame['EventKey'], str) or not frame['EventKey']
                or not isinstance(frame['EventActions'], list)):
            return None
        keys.append(frame['EventKey'])
        for action in frame['EventActions']:
            if not isinstance(action, dict):
                return None
            name = action.get('Name')
            if not synchronous(action, name):
                return None
            p = action.get('Params', {})
            if not isinstance(p, dict):
                return None
            if name in {'AwakeEntity', 'UnlockEntity'}:
                if (set(p) != {'EntityIds'} or not isinstance(p['EntityIds'], list)
                        or any(type(i) is not int or i <= 0 for i in p['EntityIds'])):
                    return None
            elif name == 'ChangeEntityState':
                if (set(p) != {'Type', 'EntityId', 'State'} or p['Type'] != 'Directly'
                        or type(p['EntityId']) is not int or not isinstance(p['State'], str) or not p['State']):
                    return None
            else:
                return None
    if len(keys) != len(set(keys)):
        return None
    return {'kind': 'deferred_sequence_content', 'state_key': key,
            'source_action': deepcopy(call), 'scope': 'isolated final media call in a recap segment',
            'local_dialogue_count': 0, 'asset_content_in_scope': False,
            'frame_order_verified': False, 'frame_callbacks_executed': False,
            'runtime_return_verified': False, 'cross_segment_effects_verified': False}


def review(result):
    """Review recap-local issues only; do not certify all task text by omission."""
    entries = []
    for segment in (result.get('recap_backbone') or {}).get('segments', []):
        evidence = segment.get('unverified_content', [])
        deferred = next((e for e in evidence if e.get('kind') == 'deferred_sequence_content'), None)
        conditional = next((e for e in evidence if e.get('kind') == 'conditional_text_route'), None)
        panel_return = next((e for e in evidence if e.get('kind') == 'panel_return_text_route'), None)
        qte_sequence = next((e for e in evidence if e.get('kind') == 'configured_qte_text_order'), None)
        if segment['status'] == 'blocked':
            category = 'missing_definition' if segment.get('error') == 'Missing flow state' else 'order_unresolved'
        elif deferred:
            category = 'media_content_deferred'
        elif conditional:
            category = 'conditional_text_ordered'
        elif panel_return:
            category = 'panel_return_text_ordered'
        elif qte_sequence:
            category = 'configured_qte_text_ordered'
        else:
            continue
        entries.append({'quest_id': result['quest_id'], 'title': result['title'],
                        'entry_index': segment['entry_index'], 'state_key': segment['state_key'],
                        'category': category, 'error': segment.get('error'),
                        'local_event_count': sum(e.get('kind') in {'dialogue', 'choice', 'narration'}
                                                 for e in segment.get('events', [])),
                        'evidence': deferred or conditional or panel_return or qte_sequence or segment.get('control_boundary')})
    groups = [{'quest_id': result['quest_id'], 'title': result['title'], 'node_id': group['node_id'],
               'state_keys': group['state_keys'], 'local_order_verified': True, 'mainline_placement_verified': False,
               'text_event_count': sum(event['kind'] in {'dialogue', 'choice', 'narration'}
                                       for segment in group['segments'] for event in segment['events'])}
              for group in (result.get('recap_backbone') or result).get('task_local_sequences', [])]
    return {'scope': 'known text in recap segments; other task and attachment order issues remain in coverage gaps',
            'categories': dict(Counter(e['category'] for e in entries)), 'entries': entries,
            'task_local_sequences': groups,
            'selected_config_route_order_verified': result['batch_coverage']['order']['selected_route_verified'],
            'whole_task_text_order_verified': False, 'asset_content_required': False}


def write_report(reviews, root):
    entries = [entry for review in reviews for entry in review['entries']]
    groups = [group for review in reviews for group in review.get('task_local_sequences', [])]
    counts = Counter(entry['category'] for entry in entries)
    unique = Counter(category for _, category in {(e['state_key'], e['category']) for e in entries})
    labels = {'missing_definition': '缺少流程定义', 'order_unresolved': '现有文本顺序待确认',
              'media_content_deferred': '演出内部内容后置', 'conditional_text_ordered': '条件路线已排序',
              'panel_return_text_ordered': '界面返回路径文本已排序',
              'configured_qte_text_ordered': 'QTE配置继续路径文本已排序'}
    result = {'scope': 'recap-local known-text ordering issues and resolved/deferred cases',
              'summary': {'occurrences_by_category': {k: counts[k] for k in labels},
                          'unique_states_by_category': {k: unique[k] for k in labels}},
              'whole_task_order_verification_count': None,
              'note': 'Recap-local counts cannot establish full-task text coverage or order',
              'entries': entries, 'task_local_sequences': groups}
    (root / '文本顺序报告.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 现有文本顺序核查', '', '范围为回顾局部片段。全任务及附录的其他顺序问题仍见覆盖报告。', '',
             '|分类|出现次数|独立状态数|', '|---|---:|---:|']
    lines += [f'|{labels[k]}|{counts[k]}|{unique[k]}|' for k in labels]
    lines += ['', '|任务|回顾位置|流程|分类|现有正文事件|', '|---|---:|---|---|---:|']
    lines += [f'|{e["quest_id"]} {e["title"]}|{e["entry_index"]}|{e["state_key"]}|{labels[e["category"]]}|{e["local_event_count"]}|' for e in entries]
    if groups:
        lines += ['', '## 主干位置待确认的任务局部顺序', '',
                  '|任务|节点|已确认局部顺序|文本事件数|', '|---|---:|---|---:|']
        lines += [f'|{g["quest_id"]} {g["title"]}|{g["node_id"]}|{" → ".join(g["state_keys"])}|{g["text_event_count"]}|' for g in groups]
    (root / '文本顺序报告.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return result
