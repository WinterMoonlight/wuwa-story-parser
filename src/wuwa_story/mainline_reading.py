"""Project an existing export into a concise, traceable mainline reading."""
from collections import Counter
import json

from .reading import reading_text
from .reading_markup import reading_markup
from .reading_templates import update_selected_strings


STORY_KINDS = {'dialogue', 'choice', 'narration', 'screen_text', 'center_text',
               'system_tip', 'attachment', 'information_board', 'ui_reference'}
PHASE_LABELS = {'EnterActions': '进入步骤', 'FinishActions': '完成步骤', 'Actions': '执行动作'}


def event_parts(events, pointer, named_values=None, start_index=0):
    parts = []

    def append(kind, text, source_pointer):
        if not text:
            return
        if kind == 'omission' and parts and parts[-1]['kind'] == kind and parts[-1]['text'] == text:
            parts[-1]['source_pointers'].append(source_pointer)
        else:
            parts.append({'kind': kind, 'text': text, 'source_pointers': [source_pointer]})

    for index, event in enumerate(events, start_index):
        source = f'{pointer}/{index}'
        kind = event.get('kind')
        if kind in STORY_KINDS:
            if '[缺失文本' in event.get('text', ''):
                append('omission', '【此处有一句尚未取得的文字】', source)
            else:
                text = reading_text({'title': '', 'events': [event], 'validation': {}},
                                    named_values=named_values).strip()
                append('text', text, source)
        elif kind == 'media_reference':
            media = event.get('media', {})
            captions = media.get('captions', [])
            if captions and media.get('caption_order_consensus'):
                for caption_index, caption in enumerate(captions):
                    text = reading_text({'title': '', 'events': [{'kind': 'dialogue',
                        'display_name': '字幕', 'text': caption['text']}], 'validation': {}},
                        named_values=named_values).strip()
                    append('text', text, f'{source}/media/captions/{caption_index}')
            else:
                append('omission', '【演出过程略】', source)
        elif kind == 'qte_reference':
            append('omission', '【互动操作过程略】', source)
        elif kind == 'recap_gap':
            append('omission', '【此处有未解析过程，接续后续剧情】', source)
        elif kind == 'unparsed_content':
            append('omission', '【此处交互过程略】', source)
    return parts


def build_mainline_reading(result):
    blocks = []
    restored_text = set()

    def add(events, pointer, scope, named_values=None, start_index=0, introduction=None):
        parts = event_parts(events, pointer, named_values, start_index)
        if parts:
            blocks.append({'source_pointer': pointer, 'scope': scope,
                           'introduction': introduction, 'parts': parts})

    backbone = result.get('recap_backbone')
    if backbone:
        ordering = 'recap_with_configured_dependency_corrections'
        values = {}
        phones = sorted(enumerate(backbone.get('phone_tip_insertions', [])),
                        key=lambda item: item[1]['entry_index'])
        phone_index = 0
        for index, segment in enumerate(backbone['segments']):
            while phone_index < len(phones) and phones[phone_index][1]['entry_index'] < segment['entry_index']:
                original_index, phone = phones[phone_index]
                add(phone['events'], f'/recap_backbone/phone_tip_insertions/{original_index}/events',
                    'anchored_phone', values, introduction='【手机消息】')
                phone_index += 1
            if segment['status'] == 'excluded_branch':
                continue
            pointer = f'/recap_backbone/segments/{index}'
            if segment.get('prefix_event_count'):
                introduction = '【本段仅取得开头，后续过程略】'
            else:
                introduction = None
            add(segment['events'], pointer + '/events', 'recap_segment', values,
                introduction=introduction)
            continuation = segment.get('current_task_continuation')
            if continuation:
                add(continuation['events'], pointer + '/current_task_continuation/events',
                    'current_task_continuation', values, introduction=continuation['scene_title'])
            for fragment_index, fragment in enumerate(segment.get('local_fragments', [])):
                add(fragment['events'], f'{pointer}/local_fragments/{fragment_index}/events',
                    'configured_continuation', values,
                    introduction='【交互过程略，以下为配置中的后续对白，返回时机待确认】')
            for attachment_index, attachment in enumerate(segment.get('unordered_attachments', [])):
                events = [{'kind': 'dialogue', 'display_name': '资料', 'text': value['text']}
                          for value in attachment.get('texts', [])]
                add(events, f'{pointer}/unordered_attachments/{attachment_index}/texts',
                    'attached_information', values,
                    introduction='【本段资料，具体显示时机待确认】')
            update_selected_strings(values, segment)
        for original_index, phone in phones[phone_index:]:
            add(phone['events'], f'/recap_backbone/phone_tip_insertions/{original_index}/events',
                'anchored_phone', values, introduction='【手机消息】')
    elif result.get('events'):
        ordering = 'selected_configuration_route'
        start = 0
        sections = sorted(enumerate(result.get('dungeon_return_sections', [])),
                          key=lambda item: item[1].get('insert_before_event', 0))
        for index, section in sections:
            if section.get('placement') != 'body':
                continue
            position = section['insert_before_event']
            add(result['events'][start:position], '/events', 'selected_route', start_index=start)
            add(section['events'], f'/dungeon_return_sections/{index}/events', 'anchored_dungeon_return')
            start = position
        add(result['events'][start:], '/events', 'selected_route', start_index=start)
        for section_index, section in enumerate(result.get('linked_recap_sections', [])):
            ordering = 'linked_recap_sections'
            for segment_index, segment in enumerate(section['segments']):
                add(segment['events'],
                    f'/linked_recap_sections/{section_index}/segments/{segment_index}/events',
                    'linked_recap_section',
                    introduction='【后续剧情：按关联回顾顺序排列】' if segment_index == 0 else None)
    elif result.get('moon_reading_draft') or result.get('jinzhou_reading_draft'):
        ordering = 'database_dialogue_continuity'
        draft_key = 'moon_reading_draft' if result.get('moon_reading_draft') else 'jinzhou_reading_draft'
        for index, entry in enumerate(result[draft_key]['entries']):
            pointer = f'/{draft_key}/entries/{index}'
            if 'gap' in entry or 'note' in entry:
                is_gap = 'gap' in entry
                blocks.append({'source_pointer': pointer, 'scope': 'unplaced_process' if is_gap else 'scene_note',
                               'introduction': None, 'parts': [
                                   {'kind': 'omission' if is_gap else 'scene_note',
                                    'text': entry['gap'] if is_gap else entry['note'],
                                    'source_pointers': [pointer]}]})
            elif 'board' in entry:
                external_index = entry['external_index']
                values = result['external_content'][external_index]['texts']
                pointer = f'/external_content/{external_index}/texts'
                blocks.append({'source_pointer': pointer, 'scope': 'dialogue_draft_board',
                               'introduction': '【心愿纸条】', 'parts': [
                                   {'kind': 'text', 'text': reading_markup('\n'.join(v['text'] for v in values)),
                                    'source_pointers': [f'{pointer}/{i}' for i in range(len(values))]}]})
            elif 'local_segment' in entry:
                group, segment = entry['local_segment']
                events = result['task_local_sequences'][group]['segments'][segment]['events']
                add(events, f'/task_local_sequences/{group}/segments/{segment}/events', 'dialogue_draft_flow')
            else:
                add(entry['segment']['events'], pointer + '/segment/events', 'dialogue_draft_flow',
                    introduction=entry.get('introduction'))
    else:
        chapter_recap = result.get('chapter_recap_order')
        groups = result.get('task_local_sequences', [])
        ordering = 'chapter_recap_order' if chapter_recap else 'local_flows_only'
        remaining = (chapter_recap['unplaced_group_indices'] if chapter_recap
                     else range(len(groups)))
        for index, entry in enumerate(chapter_recap['flow_entries'] if chapter_recap else []):
            placement = entry['local_segment']
            if 'recap_segment' in entry:
                segment = entry['recap_segment']
                add(segment['events'], f'/chapter_recap_order/flow_entries/{index}/recap_segment/events',
                    'chapter_recap_dialogue', introduction=segment['trigger'].get('introduction'))
                restored_text.update((event['state_key'], event['text_id']) for event in segment['events'])
                continue
            if placement is None:
                pointer = f'/chapter_recap_order/flow_entries/{index}'
                if blocks and blocks[-1]['scope'] == 'chapter_recap_gap':
                    blocks[-1]['parts'][0]['source_pointers'].append(pointer)
                else:
                    blocks.append({'source_pointer': pointer, 'scope': 'chapter_recap_gap',
                                   'introduction': None, 'parts': [
                                       {'kind': 'omission', 'text': '【此处回顾片段暂略】',
                                        'source_pointers': [pointer]}]})
                continue
            group_index, segment_index = placement
            group = groups[group_index]
            segment = group['segments'][segment_index]
            introduction = None
            if group.get('proof', {}).get('multiple_direct_calls'):
                stage = PHASE_LABELS[group['proof']['phase']]
                introduction = f'【{stage}时调用的局部对白，实际播放完成时机待确认】'
            add(segment['events'], f'/task_local_sequences/{group_index}/segments/{segment_index}/events',
                'chapter_recap_flow', introduction=introduction)
        for group_index in remaining:
            group = groups[group_index]
            for index, segment in enumerate(group['segments']):
                for intermediate_index, intermediate in enumerate(group.get('intermediate_content', [])):
                    if intermediate['before_segment_index'] == index:
                        add(intermediate['events'],
                            f'/task_local_sequences/{group_index}/intermediate_content/{intermediate_index}/events',
                            'local_information_board')
                introduction = '【局部剧情片段】'
                if group.get('order_scope') == 'condition_completion_to_async_call':
                    introduction = '【以下两段依次调用，与其他片段的先后待确认】' if index == 0 else None
                elif group.get('order_scope') == 'condition_completion_via_information_board':
                    introduction = '【局部连续片段：对白、资料与后续对白；整体位置待确认】' if index == 0 else None
                elif group.get('proof', {}).get('multiple_direct_calls'):
                    stage = PHASE_LABELS.get(group['proof']['phase'], '执行动作')
                    introduction = f'【{stage}时调用的局部对白；与其他片段的播放先后待确认】'
                add(segment['events'], f'/task_local_sequences/{group_index}/segments/{index}/events',
                    'local_flow', introduction=introduction)
        for group_index, group in enumerate(result.get('batch_coverage', {}).get('levelplay_local_sequences', [])):
            if group['status'] != 'local_order_only':
                continue
            introduction = '【玩法局部对白，与其他片段的先后待确认】'
            if group.get('order_scope') == 'increasing_counter_invocations':
                introduction = '【按计数递增时的调用顺序排列，实际触发及整体位置待确认】'
            for index, segment in enumerate(group['segments']):
                add(segment['events'],
                    f'/batch_coverage/levelplay_local_sequences/{group_index}/segments/{index}/events',
                    'local_gameplay_flow', introduction=introduction if index == 0 else None)

    parts = [part for block in blocks for part in block['parts']]
    retained = {pointer for part in parts if part['kind'] == 'text' for pointer in part['source_pointers']}
    omitted = Counter()
    for record in result.get('batch_coverage', {}).get('records', []):
        if (record.get('origin'), record.get('text_id')) in restored_text:
            continue
        pointer = record.get('pointer', '')
        if not pointer or not any(pointer == p or pointer.startswith(p + '/') for p in retained):
            omitted[record['category']] += 1
    text_count = sum(part['kind'] == 'text' for part in parts)
    if not text_count:
        status = 'no_ordered_body'
    elif ordering == 'local_flows_only' or (ordering == 'chapter_recap_order'
                                            and not chapter_recap.get('covers_task_groups',
                                                                      chapter_recap['covers_all_reading_groups'])):
        status = 'local_fragments_only'
    elif (any(part['kind'] == 'omission' for part in parts)
          or ordering == 'database_dialogue_continuity'
          or (ordering == 'chapter_recap_order' and chapter_recap['has_gaps'])
          or result.get('batch_coverage', {}).get('status') == 'partial_order'):
        status = 'ordered_draft_with_gaps'
    else:
        status = 'ordered_draft'
    return {'version': 1, 'policy': 'mainline_first', 'status': status, 'ordering_basis': ordering,
            'runtime_verified': False, 'blocks': blocks, 'retained_text_events': text_count,
            'omission_markers': sum(part['kind'] == 'omission' for part in parts),
            'omitted_record_counts': dict(omitted),
            'omitted_gameplay_groups': sum(bool(entry.get('gameplay')) for entry in result.get('external_content', [])),
            'source_material_location': 'Original events, recap_backbone and batch_coverage remain in this JSON'}


def mainline_reading_text(result):
    view = result.get('mainline_reading') or build_mainline_reading(result)
    lines = [result['title']]
    lines.append('【主线阅读版】保留本次所选对白；复杂活动过程与其他候选材料见同名JSON。')
    backbone = result.get('recap_backbone', {})
    if backbone.get('conditional_selections'):
        lines.append('【条件路线】按本次选择成立时的分支排列。')
    if backbone.get('conditional_rejections'):
        lines.append('【分支缺口】部分条件尚未确定，本版仅展示已取得的主干。')
    review = result.get('reading_review')
    if review:
        labels = {'readable': '可连续阅读', 'readable_with_gaps': '带明确缺口可阅读', 'materials_only': '仍是材料'}
        lines += ['【阅读验收】' + labels[review['verdict']], review['summary']]
        lines.extend('【阅读限制】' + value for value in review.get('limitations', []))
    if view.get('ordering_basis') == 'database_dialogue_continuity':
        lines.append('【按数据库对白衔接整理。段间顺序为阅读草稿，暂略的片段见同名JSON】')
    elif view.get('ordering_basis') == 'chapter_recap_order':
        lines.append('【已定位的正文按章节回顾排列】')
        if view['status'] == 'local_fragments_only':
            lines.append('【其余局部片段列在后面，与主干的先后待确认】')
        elif view['status'] == 'ordered_draft_with_gaps':
            lines.append('【部分流程或交互暂略，详情见同名JSON】')
            if result.get('chapter_recap_order', {}).get('gameplay_outside_recap'):
                lines.append('【玩法局部片段列在后面，具体位置待确认】')
    elif view['status'] == 'local_fragments_only':
        lines += ['【以下片段内部有序，片段间的先后尚未确定】']
    if view['status'] == 'no_ordered_body':
        lines += ['【当前尚未取得有序主线正文，已提取材料保存在同名JSON】']
    for block in view['blocks']:
        lines.append('')
        if block.get('introduction'):
            lines.append(block['introduction'])
        lines.extend(part['text'] for part in block['parts'])
    return '\n'.join(lines) + '\n'


def write_mainline_report(root, tasks):
    """Summarize the actual reading output independently of evidence coverage."""
    records = []
    chapter_orders = {}
    for task in tasks:
        document = json.loads((root / task['files'][0]).read_text(encoding='utf-8'))
        view = document['mainline_reading']
        recap = document.get('chapter_recap_order')
        if recap:
            chapter_orders[recap['recap_quest_id']] = recap['original_task_ids']
        records.append({'quest_id': task['quest_id'], 'title': task['title'],
                        'type_id': task['type_id'], 'files': task['files'],
                        **{key: view[key] for key in ('status', 'ordering_basis',
                           'retained_text_events', 'omission_markers', 'omitted_gameplay_groups')}})
    summary = dict(Counter(record['status'] for record in records))
    report = {'policy': 'mainline_first', 'summary': summary, 'tasks': records}
    if chapter_orders:
        report['chapter_task_orders'] = chapter_orders
    (root / '主线阅读报告.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    labels = {'ordered_draft': '有序草稿', 'ordered_draft_with_gaps': '有序草稿含略过段落',
              'local_fragments_only': '仅局部有序', 'no_ordered_body': '暂无有序正文'}
    lines = ['# 主线阅读报告', '',
             '本报告统计TXT实际呈现的内容。配置中的所选顺序尚未全部经过游戏录播核验。', '',
             '候选分支、失败结局及复杂玩法细节保存在同名JSON，TXT保留主干和简短过渡说明。', '',
             '有序草稿表示已有主干可供核对。仅局部有序和暂无有序正文的记录仍待恢复整体顺序。', '']
    if chapter_orders:
        by_id = {record['quest_id']: record for record in records}
        for recap_id, task_ids in chapter_orders.items():
            chapter = by_id.get(recap_id)
            lines += [f"## {chapter['title'] if chapter else recap_id} · 任务连读顺序", '']
            for task_id in task_ids:
                record = by_id.get(task_id)
                if record:
                    lines.append(f"1. [{record['title']}](<{record['files'][1]}>) · {labels[record['status']]}")
            lines.append('')
        lines += ['## 全部任务', '']
    lines += ['|任务|类型|阅读状态|保留文本事件|略过说明|文件|',
              '|---|---|---|---:|---:|---|']
    for record in records:
        lines.append(f"|{record['quest_id']} {record['title']}|{record['type_id']}|"
                     f"{labels[record['status']]}|{record['retained_text_events']}|"
                     f"{record['omission_markers']}|[TXT](<{record['files'][1]}>) / "
                     f"[JSON](<{record['files'][0]}>)|")
    (root / '主线阅读报告.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report
