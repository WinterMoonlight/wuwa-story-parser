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
from .text_refs import non_dialogue_reason, control_references
from .reference_diagnostics import diagnose_missing
from .speakers import SpeakerResolver
from .inventory_speakers import inventory_identity, option_context

CATEGORIES = ('confirmed_route', 'candidate_branch', 'failure_ending', 'unverified')
GAP_LABELS = {
    'conditional_recap_scenario': '按所选变量值生成条件阅读路线，外部改写与运行时仍未核验',
    'recap_backbone_only': '仅回顾段落顺序，任务额外内容未归位',
    'recap_segment_blocked': '回顾段落暂未解析，原位置保留缺口',
    'recap_difference_resolved_by_entity': '回顾额外流程已关联任务子实体交互，实时触发未验证',
    'normal_task_flows_unplaced': '正常任务流程正文已提取，跨段顺序未定位',
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
                out.append({'category': current, 'origin': origin, 'source_path': list(path + (key,)),
                            'text_id': child, 'raw_text': texts.get(child, ''),
                            'text': render_text(texts.get(child, '')), 'missing': child not in texts,
                            'source_who_id': value.get('WhoId'), 'inherited_who_id': who,
                            **inventory_identity(key, value, speakers, option_type),
                            'order_verified': False})
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
        result = Exporter(allow_incomplete=True, source=source).export(qid)
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
    recap = [flow_key(o['Flow']) for row in handbooks.get(qid, []) for _, entries in embedded(row['BinData'])
             if isinstance(entries, list) for o in entries if o.get('Flow', {}).get('FlowListName')]
    if not recap:
        gaps.append({'kind': 'missing_recap_order'})
    resolution = result.get('source', {}).get('recap_reference_resolution', {})
    unplaced = resolution.get('unplaced_task_flows', [])
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
        backbone = build_backbone(qid, handbooks.get(qid, []), states, source)
        if backbone:
            result['recap_backbone'] = backbone
            from .conditional_recap import project_conditional_recap
            selections = project_conditional_recap(backbone, nodes, source, choices)
            if selections:
                gaps.append({'kind': 'conditional_recap_scenario', 'details': selections})
            from .task_extras import review_extras
            backbone['task_only_review'] = review_extras(quest, nodes, backbone, states, source)
            gaps.append({'kind': 'recap_backbone_only', 'blocked_segments': backbone['blocked_segments']})
    records = []
    inventories = {}
    speakers = SpeakerResolver()
    controls = []
    selected = {(e.get('state_key'), e.get('text_id')) for e in result['events'] if e.get('text_id')}
    selected |= {(e['bubble']['state_key'], t.get('text_id')) for e in result.get('external_content', [])
                 if 'bubble' in e for t in e.get('texts', []) if t.get('text_id')}
    selected |= {(e['parallel_flow']['state_key'], t.get('text_id')) for e in result.get('external_content', [])
                 if 'parallel_flow' in e for t in e.get('texts', []) if t.get('text_id')}
    selected |= {(e['unplaced_flow']['state_key'], t.get('text_id')) for e in result.get('external_content', []) if 'unplaced_flow' in e for t in e.get('texts', []) if t.get('text_id')}
    if backbone:
        for si, segment in enumerate(backbone['segments']):
            if segment['status'] == 'excluded_branch':
                continue
            for ei, event in enumerate(segment['events']):
                pointer = f'/recap_backbone/segments/{si}/events/{ei}'
                records.append({'category': 'confirmed_route', 'pointer': pointer,
                                'text': event.get('text', ''), 'order_verified': False,
                                'order_scope': 'recap_segment_only', 'is_placeholder': event['kind'] == 'recap_gap'})
                if event.get('text_id'):
                    selected.add((event.get('state_key', segment['state_key']), event['text_id']))
                for ci, caption in enumerate(event.get('media', {}).get('captions', [])):
                    records.append({'category': 'confirmed_route', 'pointer': pointer+f'/media/captions/{ci}',
                                    'text': caption['text'], 'order_verified': False})
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
        from .reading_effects import FLOW_LOCK_EFFECTS, flow_lock_shape
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
        for j, event in enumerate(entry.get('phone', {}).get('events', [])):
            records.append({'category': 'unverified', 'pointer': f'/external_content/{i}/phone/events/{j}',
                            'text': event.get('text', ''), 'order_verified': False,
                            'local_phone_order_verified': True})
        gaps.append({'kind': 'external_timing_or_content', 'pointer': f'/external_content/{i}',
                     'status': entry.get('status')})
    for i, item in enumerate(result.get('task_ui_texts', [])):
        records.append({'category': 'unverified', 'pointer': f'/task_ui_texts/{i}',
                        'text': item.get('text', render_text(item.get('raw_text') or '')), 'order_verified': False})
    missing = sorted({r['text_id'] for r in records if r.get('missing')} |
                     set(result['validation'].get('missing_text_ids', [])))
    if missing:
        gaps.append({'kind': 'missing_text', 'text_ids': missing})
    gaps.extend({'kind': 'parser_unverified', 'detail': item} for item in result['validation'].get('unverified_content', []))
    gaps.append({'kind': 'runtime_and_cross_task_order_not_simulated'})
    counts = {c: sum(r['category'] == c and bool(r.get('text')) and not r.get('is_placeholder') for r in records) for c in CATEGORIES}
    source_counts = {'selected_events': len(result['events']),
                     'recap_parsed_segments': backbone['parsed_segments'] if backbone else 0,
                     'recap_blocked_segments': backbone['blocked_segments'] if backbone else 0,
                     'recap_events': sum(len(s['events']) for s in backbone['segments'] if s['status'] == 'parsed') if backbone else 0,
                     'movie_caption_texts': sum(len(e.get('media', {}).get('captions', [])) for e in result['events']),
                     'static_flow_occurrences': sum('origin' in r for r in records),
                     'external_calls_decoded': len(result.get('external_content', [])),
                     'phone_events': sum(len(e.get('phone', {}).get('events', [])) for e in result.get('external_content', [])),
                     'gameplay_texts': sum(len(e.get('texts', [])) for e in result.get('external_content', []) if 'gameplay' in e),
                     'task_ui_references': len(result.get('task_ui_texts', []))}
    result['batch_coverage'] = {
        'task_action_assessment': assess_actions(quest, nodes),
        'reading_acceptance': {'status': 'recap_draft' if backbone else 'partial_order' if unplaced else ('ordered_draft' if result['events'] else 'materials_only'),
                               'chapter_readthrough_verified': False, 'accepted': False,
                               'note': 'Ordered draft requires review of key gaps, continuity and duplicates; runtime is not simulated'},
        'version': 1, 'strict_pass': strict_record['status'] == 'exported',
        'status': 'recap_draft' if backbone else 'partial_order' if unplaced else ('selected_route' if result['events'] else 'inventory_only'),
        'counts': counts, 'source_counts': source_counts,
        'count_unit': 'text occurrences, not unique lines or completeness percentage',
        'order': {'selected_route_verified': bool(result['events']) and not unplaced, 'recap_segment_order_verified': bool(result['events']) or bool(backbone), 'recap_exact_references': bool(recap) and refs == set(recap),
                  'recap_references_reconciled': bool(entities or links or bubbles or insertions or parallels),
                  'dependencies': resolution.get('dependencies', {}),
                  'runtime_verified': False, 'cross_task_verified': False},
        'gaps': gaps, 'records': records, 'non_dialogue_controls': controls,
        'missing_text_diagnostics': diagnose_missing(records, refs, set(recap), source.rows if source is not None else rows), 'observed_external_calls': channels,
        'task_conditions': [{'node_id': n['Id'], 'condition': n.get('Condition'),
                             'exit_condition': n.get('ExitCondition'), 'failed_condition': n.get('FailedCondition')}
                            for n in nodes if any(n.get(k) for k in ('Condition', 'ExitCondition', 'FailedCondition'))],
        'scope': 'Static referenced flows and successfully decoded external sources; not all game text',
        'inventory_filter': 'Omit static occurrences matching a selected event state_key and text_id; not a branch reachability proof'}
    return result


def export_reading_batch():
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
    for i, original in enumerate(strict['records'], 1):
        qid = original['quest_id']
        result = analyze(quests[qid], nodes[qid], states, handbooks, source, original)
        result['classification'] = {k: original[k] for k in ('type_id', 'chapter', 'quest_tree_memberships')}
        files = write_result(result, root / f'Type{original["type_id"]}' / original['chapter']['folder'], quiet=True)
        coverage = {k: v for k, v in result['batch_coverage'].items() if k not in {'records', 'observed_external_calls', 'non_dialogue_controls'}}
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
             '确定路线仅表示所选配置路线已解析；不保证游戏运行时顺序。候选、失败和未核验内容均单列。',
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
    print(root, summary, flush=True)
    return root, report
