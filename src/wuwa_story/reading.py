"""Human-readable edition; structured audit evidence stays in JSON."""
from .rendering import render_text
from .reading_templates import format_templates, guide_text, update_selected_strings


def reading_exclusion_reason(result, record):
    """Hide operational labels by source fields, preserving narrative choices."""
    if record.get('kind') == 'system_option':
        return 'system_option_label'
    parts = record.get('pointer', '').strip('/').split('/')
    if len(parts) != 2 or parts[0] != 'task_ui_texts' or not parts[1].isdigit():
        return None
    items = result.get('task_ui_texts', [])
    index = int(parts[1])
    if index >= len(items):
        return None
    source_path = items[index].get('source_path', [])
    if source_path == ['TidTip']:
        return 'task_objective_label'
    if source_path and source_path[0] == 'OccupationConfig':
        return 'quest_occupation_notice'
    return None


def coverage_reading_text(result):
    coverage = result['batch_coverage']
    reading_records = [r for r in coverage['records'] if not reading_exclusion_reason(result, r)]
    lines = [result['title'], '', '以下按可信范围分组；补充材料的排列不代表剧情播放顺序。']
    backbone = result.get('recap_backbone')
    interactions = {r['state_key'] for r in (backbone or {}).get('task_only_review', [])
                    if r.get('interaction_evidence')}
    if backbone:
        lines = [result['title'], '', '【回顾顺序正文】按回顾配置逐段排列，选择保留在对话中；未解析段落原位标明，尚非完整任务路线。']
        if backbone.get('dependency_order_corrections'):
            lines[2] = '【剧情正文】以回顾为基础，按任务完成后的调用关系修正部分段落，选择保留在对话中。'
        if any(a.get('kind') == 'unconditional_option_selection' for s in backbone.get('segments', []) for a in s.get('unverified_content', [])):
            lines.append('【选项说明】部分选项的条件尚未核验，本版仅沿明确无条件的选项继续，其他选项保留为候选。')
        if backbone.get('conditional_selections'):
            lines.append('【条件阅读路线】按本次选项计算并排除另一分支；假设该选择值未被其他交互覆盖，实际触发时序尚未核验。')
        if backbone.get('conditional_rejections'):
            lines.append('【分支待核验】选择之后的状态或调用时序尚不能确定，以下保留候选分支，未筛选为单一路线。')
        if any(g['kind'] == 'recap_dependency_conflict' for g in coverage.get('gaps', [])):
            lines.append('【顺序待核验】部分回顾段落与任务调用先后不一致，暂保留回顾顺序。')
        if backbone.get('dependency_order_corrections'):
            lines.append('【顺序修正】部分段落依据任务完成后的调用关系排列，原回顾位置保留在JSON。')
        if any(u.get('kind') == 'unselected_control_actions' for s in backbone['segments']
               for u in s.get('unverified_content', [])):
            lines.append('【分支说明】仅展示本次选择的可解析对话，其他选择可能仍含未解析流程。')
        pending_phone = iter(sorted(backbone.get('phone_tip_insertions', []), key=lambda p:p['entry_index']))
        next_phone = next(pending_phone, None)
        def emit_phone_before(index):
            nonlocal next_phone
            while next_phone is not None and next_phone['entry_index'] < index:
                lines.extend(['', '【手机消息：按回顾任务提示位置排列】'])
                if next_phone.get('title'):
                    lines.append(next_phone['title'])
                lines.append(reading_text({'title':'', 'events':next_phone['events'], 'validation':{}}).strip())
                next_phone = next(pending_phone, None)
        named_values = {}
        for number, segment in enumerate(backbone['segments'], 1):
            emit_phone_before(segment['entry_index'])
            if segment['status'] == 'excluded_branch':
                continue
            if segment.get('order_origin') == 'task_finish_before_interaction':
                lines += ['', '【任务对白：按任务完成依赖补入】']
            elif segment.get('order_origin') == 'task_finish_tip':
                lines += ['', '【任务对白：按回顾任务提示位置补入】']
            else:
                lines += ['', f'【回顾第{number}段】']
            if segment.get('prefix_event_count'):
                lines.append('【本段仅展示已解析的开头，未越过后续控制缺口】')
            if any(e.get('kind') in {'terminal_text_projection', 'terminal_text_boundary'}
                   for e in segment.get('unverified_content', [])):
                lines.append('【本段对话已到结尾，任务推进结果尚未核验】')
            if any(e.get('kind') == 'qte_outcome_text_consensus' for e in segment.get('unverified_content', [])):
                lines.append('【以下对白为已配置QTE结果的共同后续，实际操作完成情况未核验】')
            if any(e.get('kind') == 'implicit_choice_retry' for e in segment.get('unverified_content', [])):
                lines.append('【本段采用可完整解析的无条件选项，原默认选项仍有控制缺口】')
            for evidence in segment.get('unverified_content', []):
                if evidence.get('kind') == 'conditional_text_route':
                    decision = next(c for c in segment['route']['choices']
                                    if c['choice_key'] == evidence['choice_key'])
                    option = decision['options'][decision['selected_index']]['text']
                    lines.append('【条件路线】按“' + option + '”可选时的分支排列，具体条件保留在JSON。')
            body = reading_text({'title': '', 'events': segment['events'], 'validation': {}}, named_values=named_values)
            lines.append(body.strip())
            continuation = segment.get('current_task_continuation')
            if continuation:
                lines.append(continuation['scene_title'])
                lines.append(reading_text({'title': '', 'events': continuation['events'], 'validation': {}}).strip())
            for fragment in segment.get('local_fragments', []):
                lines.append('【界面调用后的配置对白：实际返回及与前文的衔接待核验】')
                lines.append(reading_text({'title': '', 'events': fragment['events'], 'validation': {}}).strip())
            for attachment in segment.get('unordered_attachments', []):
                if attachment.get('kind') == 'combined_information_panel':
                    lines.append('【本段资料面板：调用位置已确认，与选项的显示先后待核验】')
                else:
                    lines.append('【本段异步界面材料：以下字段排列不代表与对白的显示先后】')
                lines.extend('界面文字：' + v['text'] for v in attachment['texts'])
            update_selected_strings(named_values, segment)
        emit_phone_before(float('inf'))
        lines += ['', '【附录：未选择、未解析或尚未定位的材料；以下排列不代表剧情顺序】']
    if result.get('sequence_execution_review'):
        lines += ['', '【顺序缺口】尚不能确定任务节点的完整先后，以下片段分别按流程内部顺序展示。']
    for group in (backbone or result).get('task_local_sequences', []):
        description = ('本段内部按流程配置排列，与其他片段的先后待确认。'
                       if group.get('order_scope') == 'single_flow_without_task_order' else
                       '以下两段按同一节点的调用先后排列，与主干的衔接位置待确认。'
                       if len(group['segments']) == 2 else
                       '以下各段按同一节点的调用先后排列，与主干的衔接位置待确认。')
        lines += ['', '【局部有序对白】' + description]
        if group['proof'].get('parallel_ancestors'):
            lines.append('【条件片段】按该分支触发后的调用顺序排列，与其他分支的先后待确认。')
        for i, segment in enumerate(group['segments']):
            if i and group['proof']['bridge_actions']:
                lines.append('【场景操作后继续】中间操作可能触发的其他内容尚未核验。')
            lines.append(reading_text({'title': '', 'events': segment['events'], 'validation': {}}).strip())
    if backbone and backbone.get('duplicate_text_flows'):
        lines.append('重复来源的相同文本仅展示一份；来源与动作差异保留在JSON，不代表两份流程等价。')
    if coverage['status'] == 'partial_order':
        lines.append('本任务仅回顾部分有序；其他正常剧情片段尚未定位先后，不能视为完整路线。')
    locally_shown = set()
    for section in result.get('dungeon_return_sections', []):
        if section.get('placement')=='body':
            continue
        lines += ['', '【副本成功转场文字：与其他片段的相对顺序待核查】']
        lines.append(reading_text({'title':'', 'events':section['events'], 'validation':{}}).strip())
    for fragment in coverage.get('levelplay_local_sequences', []):
        if fragment['status'] != 'local_order_only':
            continue
        if fragment.get('order_scope') == 'increasing_counter_invocations':
            lines += ['', '【计数递增条件下的调用顺序：实际触发及与主干的位置尚未确认】']
        else:
            lines += ['', '【玩法局部有序片段：以下按连续同步调用排列，与主干的衔接位置尚未确定】']
        dependency = fragment.get('completion_dependency', {})
        if dependency.get('task_gates'):
            lines.append('【已关联任务的玩法完成条件，但尚不能确定这段内容在主干中的位置或是否重复触发。】')
        for segment in fragment['segments']:
            lines.append(reading_text({'title':'', 'events':segment['events'], 'validation':{}}).strip())
            locally_shown.update((segment['state_key'],e['text_id']) for e in segment['events'] if e.get('text_id'))
    labels = [('confirmed_route', '已解析的所选路线'), ('candidate_branch', '候选回应及可触发对白（未确认实际发生）'),
              ('failure_ending', '失败分支及结局材料'), ('unverified', '待核验的对白、小游戏及界面材料')]
    for category, title in labels:
        entries = [r for r in reading_records if r['category'] == category and r.get('text')
                   and (r.get('origin'), r.get('text_id')) not in locally_shown
                   and not r.get('pointer','').startswith('/batch_coverage/levelplay_local_sequences/')
                   and not r.get('pointer','').startswith('/dungeon_return_sections/')
                   and not r.get('pointer', '').startswith('/recap_backbone/') and not r.get('text_duplicate_of')]
        entries = [r for r in entries if not r.get('pointer', '').startswith('/task_local_sequences/')]
        if not entries:
            continue
        lines += ['', '【'+title+'】']
        if category == 'confirmed_route':
            lines.append('依据配置生成的阅读路线，尚未模拟游戏实际运行。')
        previous_origin = None
        previous_context = None
        for entry in entries:
            if category == 'confirmed_route' and entry.get('pointer','').startswith('/events/'):
                event_index = int(entry['pointer'].split('/')[2])
                for section in result.get('dungeon_return_sections', []):
                    if section.get('placement')=='body' and section['insert_before_event']==event_index:
                        lines += ['', '【副本完成对白：按回顾任务提示定位】']
                        lines.append(reading_text({'title':'', 'events':section['events'], 'validation':{}}).strip())
            value = entry
            if entry.get('pointer'):
                value = result
                for part in entry['pointer'].strip('/').split('/'):
                    value = value[int(part)] if isinstance(value, list) else value[part]
            context = value.get('reading_context')
            if entry.get('reading_context') == 'parallel_guidance':
                context = 'parallel_guidance'
            if context != previous_context:
                if context == 'entity_interaction_in_recap_order':
                    lines.append('【实体交互：按回顾顺序排列，实际触发先后及是否必经尚未核验】')
                elif context == 'unselected_conditional_branch':
                    lines.append('【本次未选择的条件分支】')
                elif context == 'declared_entity_candidate':
                    lines.append('【任务场景交互与气泡：可触发的候选文本，出现条件及先后未核验】')
                elif context == 'entity_trigger_candidate':
                    lines.append('【任务场景触发对白：归属有配置依据，触发条件及与主干的先后尚未核验】')
                elif context == 'parallel_guidance':
                    lines.append('【教学触发对白：配置属于并行教学分支，实际播放时机待核查】')
                elif context == 'declared_levelplay_candidate':
                    lines.append('【任务场景玩法对白：归属有配置依据，触发及与主干的先后尚未核验】')
                elif previous_context:
                    lines.append('【继续回顾中的其他剧情】')
                previous_context = context
            origin = entry.get('origin') or '/'.join(entry.get('pointer', '').split('/')[:3])
            if category != 'confirmed_route' and origin != previous_origin:
                heading = '【探索交互：触发条件有记录，与主干的先后尚未确认】' if origin in interactions else '【补充片段】'
                timing = [r for r in coverage.get('entity_trigger_timing', []) if r['state_key'] == origin]
                regions = {(r['map_id'], r['common_task_region']['node_id'], r['common_task_region']['name'])
                           for r in timing if r.get('common_task_region')}
                if timing and len(regions) == 1 and all(r.get('common_task_region') for r in timing):
                    heading = '【场景触发对白·' + next(iter(regions))[2] + '：具体播放位置待确认】'
                lines += ['', heading]
                trigger = next((item for item in coverage.get('dungeon_trigger_review', [])
                                if item['state_key']==origin and item['multiple_callsites']), None)
                if trigger:
                    lines.append('【同一对白有多处触发配置，实际播放次数与先后待核查】')
                previous_origin = origin
            name = '漂泊者【选择】' if value.get('kind') == 'choice' else value.get('display_name')
            display_text = guide_text({**value, 'text': entry['text']})
            if name:
                lines.append(render_text(name)+'：'+display_text)
            else:
                lines.append(display_text)
    if not any(r.get('text') for r in reading_records):
        lines += ['', '【缺失说明】当前未提取到可阅读正文，不能据此判断原任务没有剧情。']
    else:
        lines += ['', '【待补充】部分内容的归属、触发条件或播放顺序尚未核实。']
    if any(g['kind'] == 'qte_runtime_unverified' for g in coverage['gaps']):
        lines.append('快速反应操作的成功、失败分支尚未还原为实际游玩路线。')
    if any(g['kind'] == 'missing_text' for g in coverage['gaps']):
        lines.append('部分文字引用未找到对应正文。')
        if any(d.get('shared_audio_candidates') for d in coverage.get('missing_text_diagnostics', [])):
            lines.append('缺失文字虽有共用语音的候选文本，但尚未证实可以替换，仍保留缺失。')
    if not coverage['order']['selected_route_verified'] and not backbone:
        lines.append('尚未还原可靠的任务阅读路线；以上仅为候选材料。')
    if any(e.get('status') == 'phone_body_unparsed' for e in result.get('external_content', [])):
        lines.append('手机消息正文尚未解析。')
    if any('parallel_flow' in e for e in result.get('external_content', [])):
        lines.append('并行条件下的补充对白已单列；不能确定它是否发生在正式会面之前。')
    return '\n'.join(lines)+'\n'


def reading_text(result, named_values=None):
    from .reading_markup import reading_markup
    return reading_markup(format_templates(_reading_text(result), named_values=named_values))


def _reading_text(result):
    if result.get('reading_review'):
        review = result['reading_review']
        body = dict(result)
        body.pop('reading_review')
        labels = {'readable':'可连续阅读', 'readable_with_gaps':'带明确缺口可阅读', 'materials_only':'仍是材料'}
        header = ['【阅读验收】' + labels[review['verdict']], review['summary']]
        header.extend('【阅读限制】' + limitation for limitation in review.get('limitations', []))
        return '\n'.join(header) + '\n\n' + reading_text(body)
    if 'batch_coverage' in result:
        return coverage_reading_text(result)
    lines = [result['title']]
    notes = []
    def note(text):
        if text not in notes:
            notes.append(text)
    def events(items):
        context = None
        for event in items:
            current = event.get('reading_context')
            if current != context:
                if current == 'entity_interaction_in_recap_order':
                    lines.append('【实体交互：按回顾顺序排列，实际触发先后及是否必经尚未核验】')
                elif context:
                    lines.append('【继续回顾中的其他剧情】')
                context = current
            kind = event.get('kind')
            if kind == 'quest_control':
                continue
            if kind == 'ui_reference':
                lines.append(event['text'])
                continue
            if kind == 'qte_reference':
                lines.append(event['text'])
                continue
            if kind == 'media_reference':
                if event.get('content_deferred'):
                    lines.append('【演出】内部内容后置。')
                    continue
                media = event.get('media', {})
                if media.get('captions'):
                    lines.append('【过场字幕：按配置数值的一致顺序排列】' if media['caption_order_consensus'] else '【过场字幕材料：先后尚未确认】')
                    for caption in media['captions']:
                        lines.append('字幕：' + caption['text'])
                    note('已提取配置字幕；说话人、实际播放时间及额外画面文字尚未核验。')
                else:
                    lines.append('【过场】此处有一段演出，其额外对白或字幕尚未核实。')
                continue
            name = '漂泊者【选择】' if kind == 'choice' else event.get('display_name', '旁白')
            lines.append(name + '：' + event['text'])
    if result.get('validation', {}).get('unplaced_flow_count'):
        lines.append('【以下为回顾已排列的部分剧情；其他正常剧情单列，整个任务顺序尚未补齐】')
    dungeon_sections = sorted((section for section in result.get('dungeon_return_sections', []) if section.get('placement')=='body'), key=lambda section:section['insert_before_event'])
    start = 0
    for section in dungeon_sections:
        position = section['insert_before_event']
        events(result['events'][start:position])
        lines.append('【副本完成对白：按回顾任务提示定位】')
        events(section['events'])
        start = position
    events(result['events'][start:])
    for attachment in result.get('unordered_attachments', []):
        lines.append('【异步界面材料：以下字段排列不代表与对白的显示先后】')
        lines.extend('界面文字：' + v['text'] for v in attachment['texts'])
    games = set()
    for entry in result.get('external_content', []):
        status = entry.get('status')
        if status == 'information_board_read':
            lines.append('【资料面板】')
            lines.extend(t.get('text') or render_text(t.get('raw_text') or '[缺失文本]') for t in entry.get('texts', []))
        if 'unplaced_flow' in entry:
            lines.append('【正常剧情片段：尚未确定与其他段落的先后，以下每段仅保持内部对白顺序】')
            for item in entry.get('texts', []):
                name = '漂泊者【选择】' if item.get('source_event', {}).get('kind') == 'choice' else item.get('display_name', '旁白')
                lines.append(name + '：' + item.get('text', render_text(item.get('raw_text') or '')))
            continue
        if 'gameplay' in entry:
            game = entry['gameplay']
            if game['reigns_id'] in games:
                continue
            games.add(game['reigns_id'])
            lines += [f'【小游戏·第{len(games)}部分】',
                      '以下保留不同选项和结局的文本，尚未整理成一条成功游玩路线。']
            # Only use explicit speaker records; do not infer the protagonist here.
            from .speakers import SpeakerResolver
            speakers = SpeakerResolver()
            previous_card = None
            for value in entry.get('texts', []):
                text = value.get('text', render_text(value.get('raw_text') or ''))
                if not text:
                    continue
                if 'card_id' in value:
                    if value['card_id'] != previous_card:
                        lines.append('【卡牌文本】')
                        previous_card = value['card_id']
                    lines.append(text)
                elif 'Options' in value.get('source_path', []):
                    lines.append('可选回应：' + text)
                else:
                    name = render_text(speakers.identify(value.get('who_id'))['display_name'])
                    lines.append(name + '：' + text)
            if any(c['status'] != 'read' for c in game.get('cards', [])):
                note('部分结局卡文本尚未找到。')
        elif 'parallel_flow' in entry:
            lines.append('【并行条件下的补充对白】')
            for value in entry.get('texts', []):
                lines.append(value['display_name'] + '：' + value.get('text', render_text(value['raw_text'])))
            note('这段对白是否触发、与会面剧情的先后顺序尚未核实。')
        elif 'bubble' in entry:
            lines.append('【靠近角色时的气泡对白】')
            for value in entry.get('texts', []):
                lines.append(value['display_name'] + '：' + value.get('text', render_text(value['raw_text'])))
            note('气泡对白按配置单列；是否触发及与主线的先后顺序尚未核实。')
        elif 'phone' in entry:
            lines.append('【手机消息】')
            events(entry['phone']['events'])
            if entry['phone'].get('status') == 'unparsed_message_layout':
                note('手机消息正文尚未解析。')
            note('手机消息的实际阅读时刻尚未确定。')
        elif status == 'mail_body_unavailable_in_row':
            note('任务包含一封邮件，其标题、发件人和正文尚未找到。')
        elif status in {'chapter_ui_unverified', 'teleport_transition_unverified', 'system_board_body_unresolved'}:
            note('部分界面或过场内容尚未核实。')
        elif entry.get('texts'):
            label = '引导提示' if 'guide' in entry else '补充文本'
            if entry.get('route_scope') == 'failure_branch':
                label = '失败时提示'
            lines.append('【' + label + '】')
            for value in entry['texts']:
                if value.get('purpose') == 'owner_name':
                    continue
                text = guide_text({**value, 'text': value.get('text', render_text(value.get('raw_text') or ''))})
                if text: lines.append(text)
    if result['validation'].get('missing_text_ids'):
        note('部分文本尚未找到，对应位置保留缺失提示。')
    if result['validation'].get('status') == 'needs_review':
        note('补充内容的实际出现顺序尚未全部核实。')
    if notes:
        lines += ['【待补充说明】'] + notes
    return '\n\n'.join(lines)
