"""Conservative batch coverage: extraction is not execution or completeness."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json

from .batch import Snapshot, export_mainline
from .database import embedded, texts, resolve, P, rows
from .export_task import Exporter, flow_key, flow_actions, walk, FLOW_ACTIONS, write_result
from .external import inspect_task_content, inspect_node_ui, TASK_EXTERNAL, node_context
from .coverage import TASK_EFFECTS
from .reading_effects import READING_EFFECTS
from .blockers import assess_actions
from .rendering import render_text
from .scan import diagnose_actions
from .text_refs import non_dialogue_reason, control_references, phone_media_reference, PHONE_MEDIA_TEXT
from .reference_diagnostics import diagnose_missing
from .speakers import SpeakerResolver
from .inventory_speakers import inventory_identity, option_context

CATEGORIES = ('confirmed_route', 'candidate_branch', 'failure_ending', 'unverified')
GAP_LABELS = {
    'task_sync_prefix_inserted': '唯一同步前置对白已按任务调用补入正文',
    'recap_dependency_corrected': '已依据任务完成后的调用关系修正回顾段落顺序',
    'task_finish_supplement_inserted': '任务完成后的唯一后继对白已补入正文',
    'sequence_task_order_unresolved': '单流程正文已排序，Sequence子节点执行顺序仍待确认',
    'dungeon_return_reading': '副本完成前对白已定位，其他副本流程时序待核查',
    'parallel_guidance_separated': '并行触发教学已单列，播放时机待核查',
    'entity_trigger_content': '任务声明实体的触发对白已单列，条件与主干顺序未核验',
    'entity_trigger_unresolved': '实体触发对白配置缺失或不唯一，保留诊断',
    'phone_tip_anchored': '手机消息已按唯一回顾提示定位，实际阅读时刻未核验',
    'levelplay_local_order_only': '玩法片段局部调用顺序已有依据，主干位置仍未确定',
    'declared_levelplay_content': '任务声明玩法的对白已单列，异步及跨节点顺序未核验',
    'declared_levelplay_unresolved': '任务声明玩法的配置或流程缺失，保留诊断',
    'declared_entity_content': '任务子实体交互与气泡已单列，触发及顺序未核验',
    'declared_entity_unresolved': '任务子实体配置缺失或不唯一，未据此补入文本',
    'conditional_recap_rejected': '条件路线存在覆写或调用边界疑点，未按旧变量值筛选',
    'recap_dependency_unresolved': '局部调用依赖尚未关联到唯一回顾位置',
    'recap_dependency_conflict': '局部调用依赖与回顾位置冲突，需核查',
    'conditional_recap_scenario': '按所选变量值生成条件阅读路线，外部改写与运行时仍未核验',
    'recap_backbone_only': '仅回顾段落顺序，任务额外内容未归位',
    'recap_segment_blocked': '回顾段落暂未解析，原位置保留缺口',
    'recap_difference_resolved_by_entity': '回顾额外流程已关联任务子实体交互，实时触发未验证',
    'normal_task_flows_unplaced': '正常任务流程正文已提取，跨段顺序未定位',
    'linked_recap_sections': '正常任务流程已按关联回顾区段接入，实机时序未模拟',
    'qte_runtime_unverified': 'QTE成功或失败条件及运行路线未验证',
    'task_parallel_flow_separated': '并行流程已单列，播放先后仍未确定',
    'task_flow_inserted_at_tip': '任务完成流程已按提示锚点补入',
    'task_only_bubbles_separated': '任务独有气泡已单列，触发时序未验证',
    'recap_difference_resolved_by_levelplay': '引用差异已由副本玩法配置解释',
    'route_blocked': '所选路线解析中断', 'external_extraction_blocked': '外部调用解码失败',
    'missing_recap_order': '缺少回顾顺序', 'recap_reference_difference': '回顾与任务引用不一致',
    'missing_flow_state': '流程资源缺失', 'flow_decode_blocked': '流程结构无法解码',
    'unsupported_flow_action': '流程动作未支持', 'unsupported_task_action': '任务动作未支持',
    'flow_external_calls_require_review': '流程内媒体等调用待核查',
    'external_timing_or_content': '补充内容或显示时序待核验', 'missing_text': '正文引用缺失',
    'parser_unverified': '解析器标记的待核验项', 'nested_external_calls': '嵌套外部调用未单独提取',
    'runtime_and_cross_task_order_not_simulated': '运行时及跨任务顺序未验证',
}


def inventory(value, origin, category='unverified', path=(), who=None, speakers=None, option_type=None):
    """Keep occurrence paths. Array order alone is never narrative order."""
    out = []
    if speakers is None:
        speakers = SpeakerResolver()
    if isinstance(value, dict):
        who = value.get('WhoId', who)
        for key, child in value.items():
            current = category
            if key == 'Options' and category != 'failure_ending':
                current = 'candidate_branch'
            if key in {'TidTalk', 'TidTalkOption', 'TidCenterText'} and isinstance(child, str) and child:
                # Control nodes can retain text keys without displaying speech.
                if key == 'TidTalk' and non_dialogue_reason(value):
                    continue
                visual = phone_media_reference(value) if key == 'TidTalk' else None
                record = {'category': current, 'origin': origin, 'source_path': list(path + (key,)),
                            'text_id': child, 'raw_text': texts.get(child, ''),
                            'text': render_text(texts.get(child, '')), 'missing': child not in texts,
                            'source_who_id': value.get('WhoId'), 'inherited_who_id': who,
                            **inventory_identity(key, value, speakers, option_type),
                            'order_verified': False}
                if visual:
                    record.update(text=PHONE_MEDIA_TEXT[visual['type']], missing=False,
                                  phone_media=visual, reference_kind='phone_visual')
                out.append(record)
            else:
                out.extend(inventory(child, origin, current, path + (key,), who, speakers,
                                     option_context(value) if key == 'Options' else None))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            out.extend(inventory(child, origin, category, path + (i,), who, speakers, option_type))
    return out


def ending_category(card_id, endings):
    related = [e for e in endings if card_id in [e.get('CardId'), *e.get('CardIds', [])]]
    # A card shared by success and failure is not exclusively a failure ending.
    return 'failure_ending' if related and all(e.get('IsSuccess') is False for e in related) else 'unverified'


def external_inventory(nodes, source):
    """Isolate top-level calls so one unknown payload cannot hide other sources."""
    skeleton = deepcopy(nodes)
    phases = ('EnterActions', 'FinishActions', 'Actions')
    for node in skeleton:
        for phase in phases:
            node[phase] = []
    entries, gaps = [], []
    for index, node in enumerate(nodes):
        for phase in phases:
            for ai, action in enumerate(node.get(phase, [])):
                if action.get('Name') not in TASK_EXTERNAL:
                    continue
                isolated = deepcopy(skeleton)
                isolated[index][phase] = [action]
                try:
                    decoded = inspect_task_content(isolated, source.rows, include_nested=False)
                    for entry in decoded:
                        entry['original_action_index'] = ai
                        entry['original_preceding_actions'] = node[phase][:ai]
                        entry['original_following_actions'] = node[phase][ai + 1:]
                        entry['isolation_note'] = 'Decoded independently; temporary array position is not original timing'
                    entries.extend(decoded)
                except Exception as exc:
                    gaps.append({'kind': 'external_extraction_blocked', 'node_id': node['Id'],
                                 'phase': phase, 'action_index': ai, 'action': action, 'detail': str(exc)})
    nested_count = sum(o.get('Name') in TASK_EXTERNAL and 'Params' in o for o in walk(nodes))
    attempted = len(entries) + len(gaps)
    if nested_count > attempted:
        gaps.append({'kind': 'nested_external_calls', 'observed': nested_count, 'attempted_top_level': attempted})
    return entries, gaps


def analyze(quest, nodes, states, handbooks, source, strict_record, choices=None):
    qid = quest['Id']
    gaps = []
    result = None
    try:
        result = Exporter(allow_incomplete=True, source=source, choices=choices).export(qid)
    except Exception as exc:
        gaps.append({'kind': 'route_blocked', 'detail': str(exc), 'error_type': type(exc).__name__})
    # Never retain partial events from the failed Exporter instance.
    if result is None:
        result = {'schema_version': 3, 'quest_id': qid, 'title': render_text(resolve(quest.get('TidName', ''))),
                  'source': {'quest_definition': quest, 'task_nodes': nodes},
                  'events': [], 'route': {'choices': [], 'gender': 'female'},
                  'validation': {'status': 'needs_review', 'complete_for_supported_task_shape': False,
                                 'missing_text_ids': []}}
        result['external_content'], external_gaps = external_inventory(nodes, source)
        gaps.extend(external_gaps)
        result['task_ui_texts'] = inspect_node_ui(nodes)
    refs = {flow_key(o) for o in walk([quest, nodes]) if o.get('FlowListName') and 'StateId' in o}
    recap_rows = handbooks.get(qid, [])
    recap_arrays = [entries for row in recap_rows for _, entries in embedded(row['BinData'])
                    if isinstance(entries, list)]
    recap = [flow_key(o['Flow']) for entries in recap_arrays for o in entries
             if o.get('Flow', {}).get('FlowListName')]
    recap_source_unique = len(recap_rows) == 1 and len(recap_arrays) == 1
    if not recap:
        gaps.append({'kind': 'missing_recap_order'})
    from .dependencies import dependency_report
    flow_dependencies = dependency_report(quest, nodes, recap, order_source_unique=recap_source_unique)
    for field, kind in [('recap_dependency_unresolved', 'recap_dependency_unresolved'),
                        ('recap_dependency_conflicts', 'recap_dependency_conflict')]:
        if flow_dependencies[field]:
            gaps.append({'kind': kind, 'details': flow_dependencies[field]})
    resolution = result.get('source', {}).get('recap_reference_resolution', {})
    unplaced = resolution.get('unplaced_task_flows', [])
    linked_event_pointers = {}
    if unplaced and result.get('events'):
        from .linked_recap import recover_linked_recap
        linked_review = recover_linked_recap(quest, nodes, result, states, source, choices)
        sections = linked_review.pop('sections')
        result['linked_recap_review'] = linked_review
        if sections:
            result['linked_recap_sections'] = sections
            recovered = {s['state_key'] for section in sections for s in section['segments']}
            unplaced = [item for item in unplaced if item['state_key'] not in recovered]
            result['validation']['reading_unplaced_flow_count'] = len(unplaced)
            result['validation']['linked_recap_flow_count'] = len(recovered)
            for detail in result['validation'].get('unverified_content', []):
                if detail.get('kind') == 'normal_flow_unplaced' and detail.get('state_key') in recovered:
                    detail['reading_placement'] = {'source': 'linked_recap_sections',
                                                   'resolved': True, 'runtime_verified': False}
            gaps.append({'kind': 'linked_recap_sections', 'state_keys': sorted(recovered),
                         'source_quest_ids': [s['source_quest_id'] for s in sections], 'runtime_verified': False})
    entities = resolution.get('linked_entities', [])
    if unplaced:
        gaps.append({'kind': 'normal_task_flows_unplaced', 'flows': unplaced})
    links = resolution.get('linked_levelplays', [])
    bubbles = resolution.get('separate_bubble_references', [])
    insertions = resolution.get('anchored_insertions', [])
    parallels = resolution.get('separate_parallel_references', [])
    if refs != set(recap):
        gaps.append({'kind': 'recap_difference_resolved_by_entity' if entities else 'task_parallel_flow_separated' if parallels else ('task_flow_inserted_at_tip' if insertions else ('task_only_bubbles_separated' if bubbles and not links else ('recap_difference_resolved_by_levelplay' if links else 'recap_reference_difference'))),
                     'task_only': sorted(refs-set(recap)), 'recap_only': sorted(set(recap)-refs),
                     'resolved': bool(entities or links or bubbles or insertions or parallels), 'levelplay_ids': [x['levelplay_id'] for x in links],
                     'separate_parallel_references': parallels,
                     'anchored_insertions': insertions,
                     'separate_bubble_references': bubbles})
    backbone = None
    if not result['events']:
        from .recap_backbone import build_backbone
        backbone = build_backbone(qid, handbooks.get(qid, []), states, source, choices=choices)
        if backbone:
            result['recap_backbone'] = backbone
            from .conditional_recap import project_conditional_recap
            selections = project_conditional_recap(backbone, nodes, source, choices)
            if backbone.get('conditional_rejections'):
                gaps.append({'kind': 'conditional_recap_rejected', 'details': backbone['conditional_rejections']})
            if selections:
                gaps.append({'kind': 'conditional_recap_scenario', 'details': selections})
            from .task_extras import review_extras
            backbone['task_only_review'] = review_extras(quest, nodes, backbone, states, source, choices)
            sync_prefixes = [r['proof'] for r in backbone['task_only_review']
                             if r['classification'] == 'placed_sync_dialogue_prefix']
            if sync_prefixes:
                gaps.append({'kind': 'task_sync_prefix_inserted', 'details': sync_prefixes})
            from .tip_finish_flow import insert_tip_finish_flows
            tip_insertions = insert_tip_finish_flows(quest, nodes, backbone, states, source, choices)
            if tip_insertions:
                gaps.append({'kind': 'task_flow_inserted_at_tip', 'anchored_insertions': tip_insertions})
            from .task_finish_supplement import insert_task_finish_supplements
            finish_insertions = insert_task_finish_supplements(quest, nodes, backbone, states, source, choices)
            if finish_insertions:
                restored = {(p['after_state'], p['state_key']) for p in finish_insertions}
                for gap in list(gaps):
                    if gap['kind'] == 'recap_dependency_unresolved':
                        gap['details'] = [d for d in gap['details'] if (d['from_state'], d['to_state']) not in restored]
                        if not gap['details']:
                            gaps.remove(gap)
                gaps.append({'kind': 'task_finish_supplement_inserted', 'details': finish_insertions})
            from .task_local_order import local_task_sequences
            backbone['task_local_sequences'] = local_task_sequences(quest, nodes, backbone, states, source, choices)
            from .phone_tip_anchors import phone_tip_insertions, phone_tip_diagnostics
            backbone['phone_tip_insertions'] = phone_tip_insertions(nodes, backbone, result.get('external_content', []), source=source)
            backbone['phone_tip_diagnostics'] = phone_tip_diagnostics(nodes, backbone, result.get('external_content', []), backbone['phone_tip_insertions'])
            from .recap_dependency_order import repair_dependency_order
            corrections = repair_dependency_order(quest, nodes, backbone, flow_dependencies)
            if corrections:
                corrected_edges = {(p['from_state'], p['to_state']) for p in corrections}
                for gap in list(gaps):
                    if gap['kind'] == 'recap_dependency_conflict':
                        gap['details'] = [e for e in gap['details']
                                          if (e['from_state'], e['to_state']) not in corrected_edges]
                        if not gap['details']:
                            gaps.remove(gap)
                gaps.append({'kind': 'recap_dependency_corrected', 'details': corrections})
            if backbone['phone_tip_insertions']:
                gaps.append({'kind':'phone_tip_anchored', 'messages':[p['message_id'] for p in backbone['phone_tip_insertions']]})
            gaps.append({'kind': 'recap_backbone_only', 'blocked_segments': backbone['blocked_segments']})
    if not result['events'] and not backbone and not recap:
        from .task_local_order import adjacent_task_sequences
        task_sequences = adjacent_task_sequences(quest, nodes, states, source, choices)
        from .sequence_task_review import review_sequence_task
        single_groups, sequence_review = review_sequence_task(quest, nodes, states, source, task_sequences, choices)
        task_sequences.extend(single_groups)
        from .task_local_order import independent_task_sequences
        task_sequences.extend(independent_task_sequences(quest, nodes, states, source,
                                                          task_sequences, choices))
        from .task_condition_flows import condition_task_sequences
        condition_groups, condition_review = condition_task_sequences(
            quest, nodes, states, source, task_sequences, choices)
        task_sequences.extend(condition_groups)
        from .task_local_order import connect_condition_followups
        task_sequences = connect_condition_followups(quest, nodes, states, source, task_sequences, choices)
        if condition_review:
            result['condition_flow_review'] = condition_review
        if sequence_review:
            result['sequence_execution_review'] = sequence_review
            gaps.append({'kind': 'sequence_task_order_unresolved',
                         'sequence_groups': sequence_review['sequence_groups']})
        if task_sequences:
            result['task_local_sequences'] = task_sequences
    task_sequences = (backbone or result).get('task_local_sequences', [])
    local_sequence_pointer = '/recap_backbone/task_local_sequences' if backbone else '/task_local_sequences'
    records = []
    from .parallel_guidance import guidance_evidence
    guidance = guidance_evidence(nodes, [e for entries in recap_arrays for e in entries])
    separated_events = [e for e in result['events'] if e.get('state_key') in guidance]
    if separated_events:
        result['events'] = [e for e in result['events'] if e.get('state_key') not in guidance]
        result['parallel_guidance'] = [
            {'state_key':key, 'proof':proof,
             'events':[e for e in separated_events if e.get('state_key') == key]}
            for key, proof in guidance.items() if any(e.get('state_key') == key for e in separated_events)]
        gaps.append({'kind':'parallel_guidance_separated', 'state_keys':list(guidance)})
    inventories = {}
    speakers = SpeakerResolver()
    controls = []
    selected = {(e.get('state_key'), e.get('text_id')) for e in result['events'] if e.get('text_id')}
    selected |= {(e.get('state_key'),e.get('text_id')) for e in separated_events if e.get('text_id')}
    for gi, section in enumerate(result.get('parallel_guidance', [])):
        for ei, event in enumerate(section['events']):
            records.append({'category':'candidate_branch',
                'pointer':f'/parallel_guidance/{gi}/events/{ei}', 'text':event.get('text',''),
                'reading_context':'parallel_guidance', 'order_verified':False})
    selected |= {(e['bubble']['state_key'], t.get('text_id')) for e in result.get('external_content', [])
                 if 'bubble' in e for t in e.get('texts', []) if t.get('text_id')}
    selected |= {(e['parallel_flow']['state_key'], t.get('text_id')) for e in result.get('external_content', [])
                 if 'parallel_flow' in e for t in e.get('texts', []) if t.get('text_id')}
    selected |= {(e['unplaced_flow']['state_key'], t.get('text_id')) for e in result.get('external_content', []) if 'unplaced_flow' in e for t in e.get('texts', []) if t.get('text_id')}
    for section_index, section in enumerate(result.get('linked_recap_sections', [])):
        for segment_index, segment in enumerate(section['segments']):
            for event_index, event in enumerate(segment['events']):
                pointer = f'/linked_recap_sections/{section_index}/segments/{segment_index}/events/{event_index}'
                records.append({'category': 'confirmed_route', 'pointer': pointer,
                                'text': event.get('text', ''), 'order_verified': False,
                                'order_scope': 'linked_recap_sections'})
                if event.get('text_id'):
                    pair = (segment['state_key'], event['text_id'])
                    selected.add(pair)
                    linked_event_pointers[pair] = pointer
    projected_information = {}
    for gi, group in enumerate(task_sequences):
        for si, segment in enumerate(group['segments']):
            for ei, event in enumerate(segment['events']):
                records.append({'category': 'unverified',
                    'pointer': f'{local_sequence_pointer}/{gi}/segments/{si}/events/{ei}',
                    'text': event.get('text', ''), 'order_verified': False,
                    'local_order_verified': True, 'order_scope': group['order_scope'],
                    'is_placeholder': (event.get('content_deferred', False)
                                       or event['kind'] in {'media_reference', 'unparsed_content', 'recap_gap'})})
                if event.get('text_id'):
                    selected.add((segment['state_key'], event['text_id']))
            result['validation']['missing_text_ids'].extend(segment['missing_text_ids'])
        for ii, intermediate in enumerate(group.get('intermediate_content', [])):
            for ei, event in enumerate(intermediate['events']):
                event_pointer = f'{local_sequence_pointer}/{gi}/intermediate_content/{ii}/events/{ei}'
                records.append({'category': 'unverified',
                    'pointer': event_pointer,
                    'text': event.get('text', ''), 'order_verified': False,
                    'local_order_verified': True, 'order_scope': group['order_scope']})
                for external_index, entry in enumerate(result.get('external_content', [])):
                    if (entry.get('node_id') == group['node_id'] and entry.get('phase') == intermediate['phase']
                            and entry.get('original_action_index', entry.get('action_index')) == intermediate['action_index']
                            and entry.get('source_action') == intermediate['source_action']
                            and entry.get('information_board') == event.get('information_board')):
                        for text_index, _ in enumerate(entry.get('texts', [])):
                            projected_information[external_index, text_index] = event_pointer + f'/information_board/texts/{text_index}'
    if backbone:
        for pi, insertion in enumerate(backbone.get('phone_tip_insertions', [])):
            for ei, event in enumerate(insertion['events']):
                records.append({'category':'confirmed_route',
                    'pointer':f'/recap_backbone/phone_tip_insertions/{pi}/events/{ei}',
                    'text':event.get('text',''), 'order_verified':False,
                    'order_scope':'unique_recap_tip_phone_section_only'})
        for si, segment in enumerate(backbone['segments']):
            if segment['status'] == 'excluded_branch':
                continue
            conditional = any(e.get('kind') == 'conditional_text_route' for e in segment.get('unverified_content', []))
            panel_return = any(e.get('kind') == 'panel_return_text_route' for e in segment.get('unverified_content', []))
            qte_sequence = any(e.get('kind') == 'configured_qte_text_order' for e in segment.get('unverified_content', []))
            for ei, event in enumerate(segment['events']):
                pointer = f'/recap_backbone/segments/{si}/events/{ei}'
                prefix = bool(segment.get('prefix_event_count'))
                records.append({'category': 'unverified' if prefix else 'confirmed_route', 'pointer': pointer,
                                'text': event.get('text', ''), 'order_verified': False,
                                'order_scope': ('task_sync_prefix_order' if event.get('task_placement', {}).get('kind') == 'task_sync_prefix' else
                                                'task_finish_call_order' if event.get('task_placement', {}).get('kind') == 'task_finish_supplement' else
                                                'recap_prefix_only' if prefix else 'configured_qte_recap_segment' if qte_sequence else 'panel_return_recap_segment' if panel_return else
                                                'conditional_recap_segment' if conditional else
                                                'task_finish_before_interaction' if segment.get('order_origin') == 'task_finish_before_interaction' else
                                                'unique_recap_tip_finish_flow' if segment.get('order_origin') == 'task_finish_tip' else 'recap_segment_only'),
                                'is_placeholder': event['kind'] == 'recap_gap' or event.get('content_deferred', False)})
                if event.get('text_id'):
                    selected.add((event.get('state_key', segment['state_key']), event['text_id']))
                for ci, caption in enumerate(event.get('media', {}).get('captions', [])):
                    records.append({'category': 'unverified' if prefix else 'confirmed_route', 'pointer': pointer+f'/media/captions/{ci}',
                                    'text': caption['text'], 'order_verified': False,
                                    **({'order_scope': 'recap_prefix_only'} if prefix else {})})
            for ai, attachment in enumerate(segment.get('unordered_attachments', [])):
                for ti, value in enumerate(attachment['texts']):
                    records.append({'category':'unverified', 'text':value['text'], 'order_verified':False,
                        'order_scope': ('unordered_combined_panel' if attachment.get('kind') == 'combined_information_panel'
                                        else 'unordered_async_panel'),
                        'pointer':f'/recap_backbone/segments/{si}/unordered_attachments/{ai}/texts/{ti}'})
            for fi, fragment in enumerate(segment.get('local_fragments', [])):
                for ei, event in enumerate(fragment['events']):
                    records.append({'category': 'unverified', 'text': event.get('text', ''),
                                    'order_verified': False, 'order_scope': fragment['order_scope'],
                                    'pointer': f'/recap_backbone/segments/{si}/local_fragments/{fi}/events/{ei}'})
                    if event.get('text_id'):
                        selected.add((event.get('state_key', segment['state_key']), event['text_id']))
            for tid in segment.get('missing_text_ids', []):
                result['validation']['missing_text_ids'].append(tid)
            if segment['status'] == 'blocked':
                gaps.append({'kind': 'recap_segment_blocked', 'state_key': segment['state_key'], 'detail': segment['error']})
            for item in segment.get('unverified_content', []):
                gaps.append({'kind': 'parser_unverified', 'detail': item})
    for i, event in enumerate(result['events']):
        records.append({'category': 'confirmed_route', 'pointer': f'/events/{i}',
                        'text': event.get('text', ''), 'order_verified': True,
                        'order_scope': 'selected_configuration_route_only'})
        media = event.get('media', {})
        for j, caption in enumerate(media.get('captions', [])):
            records.append({'category': 'confirmed_route' if media['caption_order_consensus'] else 'unverified',
                            'pointer': f'/events/{i}/media/captions/{j}', 'text': caption['text'],
                            'text_id': caption['text_id'], 'missing': caption['missing'],
                            'order_verified': False,
                            'relative_order_basis': 'four_numeric_tracks_consensus' if media['caption_order_consensus'] else 'unverified'})
    for key in sorted(refs | set(recap)):
        if key not in states:
            gaps.append({'kind': 'missing_flow_state', 'state_key': key})
            continue
        try:
            actions, _ = flow_actions(states[key]['BinData'])
        except Exception as exc:
            gaps.append({'kind': 'flow_decode_blocked', 'state_key': key, 'detail': str(exc)})
            continue
        controls.extend({'origin': key, **r} for r in control_references(actions, texts))
        if any(o.get('Type') == 'QTE' for o in walk(actions)):
            gaps.append({'kind': 'qte_runtime_unverified', 'state_key': key})
        unknown, channels = diagnose_actions(actions, FLOW_ACTIONS | {'PlayMovie', 'AccpetCurrentQuest'}, key)
        from .export_task import flow_restore_shape
        restores = [o for o in walk(actions) if o.get('Name') == 'ShowAllHidedGroupInFlow']
        if restores and all(flow_restore_shape(o) for o in restores):
            unknown = [a for a in unknown if a['name'] != 'ShowAllHidedGroupInFlow']
        from .reading_effects import flow_audio_state_shape
        audio_states = [o for o in walk(actions) if o.get('Name') == 'SetAudioState']
        if audio_states and all(flow_audio_state_shape(o) for o in audio_states):
            unknown = [a for a in unknown if a['name'] != 'SetAudioState']
        from .camera_effects import CAMERA_EFFECTS, camera_shape
        from .npc_perform import npc_perform_shape
        from .sublevels import switch_shape
        from .screen_effects import screen_stop_shape
        from .client_scene_effects import CLIENT_SCENE_EFFECTS, client_scene_shape
        for scene_name in CLIENT_SCENE_EFFECTS:
            scene_actions = [o for o in walk(actions) if o.get('Name') == scene_name]
            if scene_actions and all(client_scene_shape(o) for o in scene_actions):
                unknown = [a for a in unknown if a['name'] != scene_name]
        stops = [o for o in walk(actions) if o.get('Name') == 'StopUiScreenEffect']
        if stops and all(screen_stop_shape(o) for o in stops):
            unknown = [a for a in unknown if a['name'] != 'StopUiScreenEffect']
        switches = [o for o in walk(actions) if o.get('Name') == 'SwitchSubLevels']
        if switches and all(switch_shape(o) for o in switches):
            unknown = [a for a in unknown if a['name'] != 'SwitchSubLevels']
        performances = [o for o in walk(actions) if o.get('Name') == 'FlowDefineNpcGroupPerform']
        if performances and all(npc_perform_shape(o) for o in performances):
            unknown = [a for a in unknown if a['name'] != 'FlowDefineNpcGroupPerform']
        from .reading_effects import FLOW_LOCK_EFFECTS, flow_lock_shape, ENTITY_LOCK_EFFECTS, entity_lock_shape
        for entity_lock_name in ENTITY_LOCK_EFFECTS:
            entity_locks = [o for o in walk(actions) if o.get('Name') == entity_lock_name]
            if entity_locks and all(entity_lock_shape(o) for o in entity_locks):
                unknown = [o for o in unknown if o['name'] != entity_lock_name]
        for lock_name in FLOW_LOCK_EFFECTS:
            lock_actions = [o for o in walk(actions) if o.get('Name') == lock_name]
            if lock_actions and all(flow_lock_shape(o) for o in lock_actions):
                unknown = [a for a in unknown if a['name'] != lock_name]
        for camera_name in CAMERA_EFFECTS:
            camera_actions = [o for o in walk(actions) if o.get('Name') == camera_name]
            if camera_actions and all(camera_shape(o) for o in camera_actions):
                unknown = [a for a in unknown if a['name'] != camera_name]
        gaps.extend({'kind': 'unsupported_flow_action', **a} for a in unknown)
        # Failure classification requires exclusive configuration evidence.
        owners = [n for n in nodes if any(flow_key(o) == key for o in walk(n)
                  if o.get('FlowListName') and 'StateId' in o)]
        failure = False
        try:
            failure = bool(owners) and all(node_context(n, nodes)['route_scope'] == 'failure_branch' for n in owners)
        except (ValueError, KeyError):
            pass
        inventories[key] = inventory(actions, key, 'failure_ending' if failure else 'unverified', speakers=speakers)
        records.extend(r for r in inventories[key] if (key, r['text_id']) not in selected)
        if channels:
            gaps.append({'kind': 'flow_external_calls_require_review', 'state_key': key, 'calls': channels})
    # Explicit ownership permits candidate inventory, not a new ordered flow reference.
    from .declared_entity_content import declared_entity_content
    child_links, child_gaps = declared_entity_content(quest, source)
    child_keys = sorted({link['state_key'] for link in child_links} - refs - set(recap))
    child_occurrences = 0
    for key in child_keys:
        if key not in states:
            child_gaps.append({'state_key': key, 'reason': 'missing_candidate_flow'})
            continue
        try:
            actions, _ = flow_actions(states[key]['BinData'])
        except (ValueError, KeyError, TypeError) as exc:
            child_gaps.append({'state_key': key, 'reason': 'candidate_decode_failed', 'detail': str(exc)})
            continue
        items = inventory(actions, key, 'candidate_branch', speakers=speakers)
        for item in items:
            item.update(reading_context='declared_entity_candidate', mandatory_verified=False)
        added = [r for r in items if (key, r['text_id']) not in selected]
        records.extend(added)
        child_occurrences += len(added)
        # Do not fold independently triggered candidates into recap duplicates.
    if child_occurrences:
        gaps.append({'kind': 'declared_entity_content', 'text_occurrences': child_occurrences,
                     'state_keys': child_keys})
    if child_gaps:
        gaps.append({'kind': 'declared_entity_unresolved', 'details': child_gaps})
    from .declared_levelplay import declared_levelplays
    play_links, play_gaps, play_audits = declared_levelplays(quest, nodes,
        [e for entries in recap_arrays for e in entries], source)
    from .dungeon_candidates import dungeon_candidates
    dungeon_links, dungeon_gaps, dungeon_audits = dungeon_candidates(nodes, source)
    play_links.extend(dungeon_links)
    play_gaps.extend(dungeon_gaps)
    known_play_ids = {audit['levelplay_id'] for audit in play_audits}
    play_audits.extend(audit for audit in dungeon_audits if audit['levelplay_id'] not in known_play_ids)
    from .dungeon_return_text import dungeon_return_sections
    result['dungeon_return_sections'] = dungeon_return_sections(result, nodes, dungeon_audits, source)
    if result['dungeon_return_sections']:
        gaps.append({'kind':'dungeon_return_reading', 'sections':len(result['dungeon_return_sections'])})
    for si, section in enumerate(result['dungeon_return_sections']):
        for ei, event in enumerate(section['events']):
            records.append({'category':'confirmed_route' if section.get('placement')=='body' else 'candidate_branch', 'pointer':f'/dungeon_return_sections/{si}/events/{ei}',
                            'text':event.get('text',''), 'order_verified':False,
                            'order_scope':'dungeon_completion_recap_tip'})
    return_keys = {key for section in result['dungeon_return_sections'] for key in section['state_keys']}
    play_keys = sorted({link['state_key'] for link in play_links} - refs - set(recap) - set(child_keys) - return_keys)
    from .dungeon_trigger_review import trigger_review
    dungeon_triggers = trigger_review(dungeon_audits, dungeon_links, set(play_keys))
    from .entity_trigger_content import entity_trigger_content
    trigger_links, trigger_gaps = entity_trigger_content(quest, source)
    trigger_keys = sorted({link['state_key'] for link in trigger_links} - refs - set(recap) - set(child_keys) - set(play_keys))
    from .entity_trigger_timing import entity_trigger_timing
    trigger_timing = entity_trigger_timing(quest, nodes,
        [link for link in trigger_links if link['state_key'] in trigger_keys], backbone, source)
    trigger_occurrences = 0
    for key in trigger_keys:
        if key not in states:
            trigger_gaps.append({'state_key': key, 'reason': 'missing_candidate_flow'})
            continue
        try:
            actions, _ = flow_actions(states[key]['BinData'])
        except (ValueError, KeyError, TypeError) as exc:
            trigger_gaps.append({'state_key': key, 'reason': 'candidate_decode_failed', 'detail': str(exc)})
            continue
        items = inventory(actions, key, 'candidate_branch', speakers=speakers)
        for item in items:
            item.update(reading_context='entity_trigger_candidate', mandatory_verified=False,
                        ownership_link_indices=[i for i, link in enumerate(trigger_links) if link['state_key'] == key])
        added = [r for r in items if (key, r['text_id']) not in selected]
        records.extend(added)
        trigger_occurrences += len(added)
    if trigger_occurrences:
        gaps.append({'kind': 'entity_trigger_content', 'text_occurrences': trigger_occurrences,
                     'state_keys': trigger_keys})
    if trigger_gaps:
        gaps.append({'kind': 'entity_trigger_unresolved', 'details': trigger_gaps})
    play_occurrences = 0
    for key in play_keys:
        if key not in states:
            play_gaps.append({'state_key': key, 'reason': 'missing_candidate_flow'})
            continue
        try:
            actions, fields = flow_actions(states[key]['BinData'])
        except (ValueError, KeyError, TypeError) as exc:
            play_gaps.append({'state_key': key, 'reason': 'candidate_decode_failed', 'detail': str(exc)})
            continue
        # A candidate is a static inventory, not execution of its action list.
        items = inventory(actions, key, 'candidate_branch', speakers=speakers)
        for item in items:
            item.update(reading_context='declared_levelplay_candidate', mandatory_verified=False)
        added = [r for r in items if (key, r['text_id']) not in selected]
        records.extend(added)
        play_occurrences += len(added)
    if play_occurrences:
        gaps.append({'kind': 'declared_levelplay_content', 'text_occurrences': play_occurrences,
                     'state_keys': play_keys})
    if play_gaps:
        gaps.append({'kind': 'declared_levelplay_unresolved', 'details': play_gaps})
    from .levelplay_order import local_sequences
    play_sequences = local_sequences(play_audits, play_links, states, source, set(play_keys), choices)
    from .levelplay_completion import completion_evidence
    from .node_order_evidence import node_order_audit
    for fragment in play_sequences:
        audit = next(a for a in play_audits if a['levelplay_id'] == fragment['levelplay_id'])
        fragment['completion_dependency'] = completion_evidence(audit, fragment['node_id'], nodes,
            [e for entries in recap_arrays for e in entries])
        fragment['node_execution_evidence'] = node_order_audit(audit, fragment, nodes,
            [e for entries in recap_arrays for e in entries], quest['Id'], source)
    from .counter_order import counter_sequences
    used_local_keys = {key for fragment in play_sequences for key in fragment['state_keys']}
    play_sequences.extend(counter_sequences(play_audits, play_links, states, source,
                                           set(play_keys) - used_local_keys, choices))
    local_ordered = [s for s in play_sequences if s['status'] == 'local_order_only']
    if local_ordered:
        gaps.append({'kind':'levelplay_local_order_only','fragments':len(local_ordered)})
    local_caption_count = 0
    for fi, fragment in enumerate(play_sequences):
        if fragment['status'] != 'local_order_only':
            continue
        for si, segment in enumerate(fragment['segments']):
            for ei, event in enumerate(segment['events']):
                for ci, caption in enumerate(event.get('media', {}).get('captions', [])):
                    records.append({'category':'candidate_branch',
                        'pointer':f'/batch_coverage/levelplay_local_sequences/{fi}/segments/{si}/events/{ei}/media/captions/{ci}',
                        'text':caption['text'], 'text_id':caption['text_id'], 'missing':caption['missing'],
                        'order_verified':False,'order_scope':'local_configured_caption_track_only'})
                    local_caption_count += 1
    if backbone:
        from .recap_backbone import duplicate_text_flows
        excluded_keys = {s['state_key'] for s in backbone['segments'] if s['status'] == 'excluded_branch'}
        included_keys = {s['state_key'] for s in backbone['segments'] if s['status'] == 'parsed'}
        for record in records:
            if record.get('origin') in excluded_keys - included_keys:
                record.update(category='candidate_branch', reading_context='unselected_conditional_branch')
        backbone['duplicate_text_flows'] = duplicate_text_flows(inventories, set(recap), states)
        duplicates = {d['state_key']: d['text_duplicate_of'] for d in backbone['duplicate_text_flows']}
        for record in records:
            if record.get('origin') in duplicates:
                record['text_duplicate_of'] = duplicates[record['origin']]
    unknown, channels = diagnose_actions([quest, nodes], TASK_EFFECTS | TASK_EXTERNAL | READING_EFFECTS | {'PlayFlow'}, 'task')
    gaps.extend({'kind': 'unsupported_task_action', **a} for a in unknown)
    for i, entry in enumerate(result.get('external_content', [])):
        for j, item in enumerate(entry.get('texts', [])):
            category = ending_category(item.get('card_id'), entry.get('gameplay', {}).get('endings', []))
            if 'bubble' in entry:
                category = 'candidate_branch'
            if category != 'failure_ending' and 'Options' in item.get('source_path', []):
                category = 'candidate_branch'
            if entry.get('route_scope') == 'failure_branch':
                category = 'failure_ending'
            records.append({'category': category, 'pointer': f'/external_content/{i}/texts/{j}',
                            'text': item.get('text', render_text(item.get('raw_text') or '')),
                            'order_verified': False})
            if (i, j) in projected_information:
                records[-1].update(counted_elsewhere=True, text_duplicate_of=projected_information[i, j])
            linked_pointer = linked_event_pointers.get((entry.get('unplaced_flow', {}).get('state_key'), item.get('text_id')))
            if linked_pointer:
                records[-1].update(counted_elsewhere=True, text_duplicate_of=linked_pointer)
        for j, event in enumerate(entry.get('phone', {}).get('events', [])):
            anchor_index = next((pi for pi, p in enumerate((backbone or {}).get('phone_tip_insertions', []))
                                 if p['external_index']==i), None)
            records.append({'category': 'unverified', 'pointer': f'/external_content/{i}/phone/events/{j}',
                            'text': event.get('text', ''), 'order_verified': False,
                            **({'text_duplicate_of':f'/recap_backbone/phone_tip_insertions/{anchor_index}/events/{j}',
                                'counted_elsewhere':True} if anchor_index is not None else {}),
                            'local_phone_order_verified': True})
        result['validation']['missing_text_ids'].extend(entry.get('phone', {}).get('missing_text_ids', []))
        gaps.append({'kind': 'external_timing_or_content', 'pointer': f'/external_content/{i}',
                     'status': entry.get('status')})
    for i, item in enumerate(result.get('task_ui_texts', [])):
        records.append({'category': 'unverified', 'pointer': f'/task_ui_texts/{i}',
                        'text': item.get('text', render_text(item.get('raw_text') or '')), 'order_verified': False})
    from .reading import reading_exclusion_reason
    for record in records:
        reason = reading_exclusion_reason(result, record)
        if reason:
            record['reading_exclusion_reason'] = reason
    missing = sorted({r['text_id'] for r in records if r.get('missing')} |
                     set(result['validation'].get('missing_text_ids', [])))
    if missing:
        gaps.append({'kind': 'missing_text', 'text_ids': missing})
    gaps.extend({'kind': 'parser_unverified', 'detail': item} for item in result['validation'].get('unverified_content', []))
    gaps.append({'kind': 'runtime_and_cross_task_order_not_simulated'})
    counts = {c: sum(r['category'] == c and bool(r.get('text')) and not r.get('is_placeholder') and not r.get('counted_elsewhere') for r in records) for c in CATEGORIES}
    source_counts = {'selected_events': len(result['events']),
                     'linked_recap_events': sum(len(s['events']) for section in result.get('linked_recap_sections', [])
                                                for s in section['segments']),
                     'task_finish_supplement_flows': len((backbone or {}).get('task_finish_supplements', [])),
                     'task_finish_supplement_events': sum(e.get('task_placement', {}).get('kind') == 'task_finish_supplement'
                         for s in (backbone or {}).get('segments', []) for e in s['events']),
                     'recap_dependency_order_corrections': len((backbone or {}).get('dependency_order_corrections', {}).get('proofs', [])),
                     'task_local_sequence_groups': len(task_sequences),
                     'task_local_sequence_events': sum(len(s['events']) for g in task_sequences
                         for s in g['segments'] + g.get('intermediate_content', [])),
                     'dungeon_return_body_events': sum(len(s['events']) for s in result['dungeon_return_sections'] if s.get('placement')=='body'),
                     'dungeon_return_supplement_events': sum(len(s['events']) for s in result['dungeon_return_sections'] if s.get('placement')!='body'),
                     'recap_parsed_segments': sum(s['status'] == 'parsed' and not s.get('order_origin', '').startswith('task_finish')
                                                  for s in backbone['segments']) if backbone else 0,
                     'task_tip_inserted_segments': len(backbone.get('tip_flow_insertions', [])) if backbone else 0,
                     'task_tip_inserted_events': sum(len(s['events']) for s in backbone['segments']
                                                     if s.get('order_origin', '').startswith('task_finish')) if backbone else 0,
                     'recap_blocked_segments': backbone['blocked_segments'] if backbone else 0,
                     'recap_prefix_segments': sum(bool(s.get('prefix_event_count')) for s in backbone['segments']) if backbone else 0,
                     'recap_prefix_events': sum(s.get('prefix_event_count',0) for s in backbone['segments']) if backbone else 0,
                     'recap_unresolved_ui_fragment_events': sum(len(f['events']) for s in backbone['segments']
                                                               for f in s.get('local_fragments', [])) if backbone else 0,
                     'recap_unordered_panel_texts': sum(len(a['texts']) for s in backbone['segments'] for a in s.get('unordered_attachments',[])) if backbone else 0,
                     'recap_events': sum(len(s['events']) for s in backbone['segments'] if s['status'] == 'parsed') if backbone else 0,
                     'movie_caption_texts': sum(len(e.get('media', {}).get('captions', [])) for e in result['events']),
                     'static_flow_occurrences': sum('origin' in r for r in records),
                     'declared_entity_candidate_occurrences': child_occurrences,
                     'entity_trigger_candidate_occurrences': trigger_occurrences,
                     'entity_trigger_timing_reviews': len(trigger_timing),
                     'phone_tip_sections': len((backbone or {}).get('phone_tip_insertions', [])),
                     'phone_tip_events': sum(len(p['events']) for p in (backbone or {}).get('phone_tip_insertions', [])),
                     'declared_levelplay_candidate_occurrences': play_occurrences,
                     'levelplay_local_ordered_fragments': len(local_ordered),
                     'levelplay_counter_ordered_fragments': sum(
                         fragment.get('order_scope') == 'increasing_counter_invocations' for fragment in local_ordered),
                     'levelplay_local_caption_texts': local_caption_count,
                     'external_calls_decoded': len(result.get('external_content', [])),
                     'phone_events': sum(len(e.get('phone', {}).get('events', [])) for e in result.get('external_content', [])),
                     'gameplay_texts': sum(len(e.get('texts', [])) for e in result.get('external_content', []) if 'gameplay' in e),
                     'task_ui_references': len(result.get('task_ui_texts', [])),
                     'reading_excluded_labels': sum(bool(r.get('reading_exclusion_reason')) for r in records)}
    result['batch_coverage'] = {
        'task_action_assessment': assess_actions(quest, nodes),
        'reading_acceptance': {'status': 'recap_draft' if backbone or result.get('linked_recap_sections') else 'partial_order' if unplaced else ('ordered_draft' if result['events'] else 'materials_only'),
                               'chapter_readthrough_verified': False, 'accepted': False,
                               'note': 'Ordered draft requires review of key gaps, continuity and duplicates; runtime is not simulated'},
        'version': 1, 'strict_pass': strict_record['status'] == 'exported',
        'status': 'recap_draft' if backbone or result.get('linked_recap_sections') else 'partial_order' if unplaced else ('selected_route' if result['events'] else 'inventory_only'),
        'counts': counts, 'source_counts': source_counts,
        'count_unit': 'text occurrences, not unique lines or completeness percentage',
        'order': {'source_priority': ['task_call_dependencies', 'entity_or_gameplay_trigger_dependencies', 'recap_fallback'],
                  'selected_route_verified': bool(result['events']) and not unplaced and not result.get('linked_recap_sections')
                  and not flow_dependencies['recap_dependency_conflicts']
                  and not flow_dependencies['recap_dependency_unresolved'], 'recap_segment_order_verified': bool(result['events']) or bool(backbone), 'recap_exact_references': bool(recap) and refs == set(recap),
                  'recap_references_reconciled': bool(entities or links or bubbles or insertions or parallels),
                  'dependencies': flow_dependencies,
                  'runtime_verified': False, 'cross_task_verified': False},
        'gaps': gaps, 'records': records, 'non_dialogue_controls': controls,
        'declared_entity_links': child_links,
        'entity_trigger_links': trigger_links,
        'entity_trigger_timing': trigger_timing,
        'declared_levelplay_links': play_links, 'declared_levelplay_audit': play_audits,
        'dungeon_trigger_review': dungeon_triggers,
        'levelplay_local_sequences': play_sequences,
        'missing_text_diagnostics': diagnose_missing(records, refs, set(recap), source.rows if source is not None else rows), 'observed_external_calls': channels,
        'task_conditions': [{'node_id': n['Id'], 'condition': n.get('Condition'),
                             'exit_condition': n.get('ExitCondition'), 'failed_condition': n.get('FailedCondition')}
                            for n in nodes if any(n.get(k) for k in ('Condition', 'ExitCondition', 'FailedCondition'))],
        'scope': 'Static referenced flows and successfully decoded external sources; not all game text',
        'inventory_filter': 'Omit static occurrences matching a selected event state_key and text_id; not a branch reachability proof'}
    from .text_order import review
    result['batch_coverage']['text_order_review'] = review(result)
    if not result.get('events') and not result.get('recap_backbone'):
        from .sequence_dependencies import review_sequence_dependencies
        result['sequence_dependency_review'] = review_sequence_dependencies(
            quest, nodes, source, result.get('task_local_sequences', []), play_audits)
    return result


def export_reading_batch():
    from .remaining_blockers import collect_blockers, collect_unresolved_choices, write_report as write_blocker_report
    root, strict = export_mainline()
    root = root / '覆盖阅读版'
    root.mkdir()
    source = Snapshot()
    nodes, handbooks = defaultdict(list), defaultdict(list)
    for row in source.rows('db_QuestNodeData.db', 'questnodedata'):
        nodes[int(row['Key'].split('_')[0])].append(embedded(row['BinData'])[0][1])
    for row in source.rows('db_PlotHandBook.db', 'plothandbookconfig'):
        handbooks[row['QuestId']].append(row)
    states = {r['StateKey']: r for r in source.rows('db_flowState.db', 'flowstate')}
    quests = {q['Id']: q for r in source.rows('db_QuestData.db', 'questdata') for _, q in embedded(r['BinData']) if isinstance(q, dict)}
    report = []
    blocker_cases = []
    unresolved_choices = []
    text_order_reviews = []
    for i, original in enumerate(strict['records'], 1):
        qid = original['quest_id']
        result = analyze(quests[qid], nodes[qid], states, handbooks, source, original)
        result['classification'] = {k: original[k] for k in ('type_id', 'chapter', 'quest_tree_memberships')}
        files = write_result(result, root / f'Type{original["type_id"]}' / original['chapter']['folder'], quiet=True)
        blocker_cases.extend(collect_blockers(result, [p.relative_to(root).as_posix() for p in files]))
        unresolved_choices.extend(collect_unresolved_choices(result, [p.relative_to(root).as_posix() for p in files]))
        text_order_reviews.append(result['batch_coverage']['text_order_review'])
        coverage = {k: v for k, v in result['batch_coverage'].items() if k not in {'records', 'observed_external_calls', 'non_dialogue_controls', 'declared_entity_links', 'entity_trigger_links', 'entity_trigger_timing', 'declared_levelplay_links', 'declared_levelplay_audit', 'levelplay_local_sequences', 'dungeon_trigger_review'}}
        report.append({'quest_id': qid, 'title': result['title'], 'type_id': original['type_id'], **coverage,
                       'files': [p.relative_to(root).as_posix() for p in files]})
        if i % 10 == 0:
            print(f'Coverage {i}/{len(strict["records"])}', flush=True)
    summary = {'tasks': len(report), 'strict_pass': sum(r['strict_pass'] for r in report),
               'status': dict(Counter(r['status'] for r in report)),
               'tasks_with_readable_text': sum(bool(sum(r['counts'].values())) for r in report),
               'gap_task_counts': dict(Counter(k for r in report for k in {g['kind'] for g in r['gaps']}))}
    hashes = {**strict['source_sha256'], **{file: hashlib.sha256((P / file).read_bytes()).hexdigest() for file, _ in source.cache}}
    (root / '覆盖报告.json').write_text(json.dumps({'summary': summary, 'source_sha256': hashes, 'tasks': report}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 批量覆盖阅读版', '',
             f'任务 {summary["tasks"]}；严格通过 {summary["strict_pass"]}；可提取到正文 {summary["tasks_with_readable_text"]}。',
             f'已生成所选配置路线 {summary["status"].get("selected_route", 0)}；部分有序 {summary["status"].get("partial_order", 0)}；回顾主干草稿 {summary["status"].get("recap_draft", 0)}；仅候选材料 {summary["status"].get("inventory_only", 0)}。', '',
             '本表统计JSON中的完整提取材料。TXT按主线阅读投影展示，具体显示范围见主线阅读报告。',
             '确定路线表示所选配置路线已解析，游戏运行时顺序仍待核验。候选、失败和未核验内容保存在JSON。',
             '数字是文本出现次数，不是唯一台词数或完整率。所有任务保留文件；无正文也不计成功。', '',
             '|任务|严格通过|确定路线|候选分支|失败结局|未核验|所选路线顺序|缺口类型|文件|',
             '|---|---|---:|---:|---:|---:|---|---|---|']
    for r in report:
        cs = r['counts']
        cells = [str(r['quest_id'])+' '+r['title'], str(r['strict_pass']), *[str(cs[c]) for c in CATEGORIES],
                 '配置路线已解析' if r['order']['selected_route_verified'] else '未验证',
                 '、'.join(GAP_LABELS.get(k, k) for k in sorted({g['kind'] for g in r['gaps']})),
                 f'[TXT](<{r["files"][1]}>) / [JSON](<{r["files"][0]}>)']
        lines.append('| '+' | '.join(cells)+' |')
    (root / '覆盖报告.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    write_blocker_report(blocker_cases, root, unresolved_choices)
    from .text_order import write_report as write_text_order_report
    write_text_order_report(text_order_reviews, root)
    from .mainline_reading import write_mainline_report
    write_mainline_report(root, report)
    print(root, summary, flush=True)
    return root, report
