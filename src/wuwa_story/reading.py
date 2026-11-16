"""Human-readable edition; structured audit evidence stays in JSON."""
from .rendering import render_text


def coverage_reading_text(result):
    coverage = result['batch_coverage']
    lines = [result['title'], '', '以下按可信范围分组；补充材料的排列不代表剧情播放顺序。']
    backbone = result.get('recap_backbone')
    interactions = {r['state_key'] for r in (backbone or {}).get('task_only_review', [])
                    if r.get('interaction_evidence')}
    if backbone:
        lines = [result['title'], '', '【回顾顺序正文】按回顾配置逐段排列，选择保留在对话中；未解析段落原位标明，尚非完整任务路线。']
        if backbone.get('conditional_selections'):
            lines.append('【条件阅读路线】按本次选项计算并排除另一分支；假设该选择值未被其他交互覆盖，实际触发时序尚未核验。')
        for number, segment in enumerate(backbone['segments'], 1):
            if segment['status'] == 'excluded_branch':
                continue
            lines += ['', f'【回顾第{number}段】']
            body = reading_text({'title': '', 'events': segment['events'], 'validation': {}})
            lines.append(body.strip())
        lines += ['', '【附录：未选择、未解析或尚未定位的材料；以下排列不代表剧情顺序】']
        if backbone.get('duplicate_text_flows'):
            lines.append('重复来源的相同文本仅展示一份；来源与动作差异保留在JSON，不代表两份流程等价。')
    if coverage['status'] == 'partial_order':
        lines.append('本任务仅回顾部分有序；其他正常剧情片段尚未定位先后，不能视为完整路线。')
    labels = [('confirmed_route', '已解析的所选路线'), ('candidate_branch', '候选回应及可触发对白（未确认实际发生）'),
              ('failure_ending', '失败分支及结局材料'), ('unverified', '待核验的对白、小游戏及界面材料')]
    for category, title in labels:
        entries = [r for r in coverage['records'] if r['category'] == category and r.get('text')
                   and not r.get('pointer', '').startswith('/recap_backbone/') and not r.get('text_duplicate_of')]
        if not entries:
            continue
        lines += ['', '【'+title+'】']
        if category == 'confirmed_route':
            lines.append('依据配置生成的阅读路线，尚未模拟游戏实际运行。')
        previous_origin = None
        previous_context = None
        for entry in entries:
            value = entry
            if entry.get('pointer'):
                value = result
                for part in entry['pointer'].strip('/').split('/'):
                    value = value[int(part)] if isinstance(value, list) else value[part]
            context = value.get('reading_context')
            if context != previous_context:
                if context == 'entity_interaction_in_recap_order':
                    lines.append('【实体交互：按回顾顺序排列，实际触发先后及是否必经尚未核验】')
                elif context == 'unselected_conditional_branch':
                    lines.append('【本次未选择的条件分支】')
                elif previous_context:
                    lines.append('【继续回顾中的其他剧情】')
                previous_context = context
            origin = entry.get('origin') or '/'.join(entry.get('pointer', '').split('/')[:3])
            if category != 'confirmed_route' and origin != previous_origin:
                lines += ['', '【探索交互：触发条件有记录，与主干的先后尚未确认】' if origin in interactions else '【补充片段】']
                previous_origin = origin
            name = '漂泊者【选择】' if value.get('kind') == 'choice' else value.get('display_name')
            if name:
                lines.append(render_text(name)+'：'+entry['text'])
            else:
                lines.append(entry['text'])
    if not any(r.get('text') for r in coverage['records']):
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


def reading_text(result):
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
            if kind == 'media_reference':
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
    events(result['events'])
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
                text = value.get('text', render_text(value.get('raw_text') or ''))
                if text: lines.append(text)
    if result['validation'].get('missing_text_ids'):
        note('部分文本尚未找到，对应位置保留缺失提示。')
    if result['validation'].get('status') == 'needs_review':
        note('补充内容的实际出现顺序尚未全部核实。')
    if notes:
        lines += ['【待补充说明】'] + notes
    return '\n\n'.join(lines)
