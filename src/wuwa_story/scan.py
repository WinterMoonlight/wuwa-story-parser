"""Rank mainline cases using structural diversity and independently checkable order."""
from collections import Counter, defaultdict
import json
from .batch import Snapshot
from .database import embedded, resolve, O
from .export_task import walk, flow_key, FLOW_ACTIONS
from .coverage import TASK_EFFECTS


CONTENT_CHANNELS = {
    'PlayMovie': '视频及字幕', 'PhoneSystemInteract': '手机消息',
    'SendNpcMail': '邮件', 'OpenSimpleGameplay': '小游戏及其文本',
    'CommonTip': '任务提示文字', 'AddPlayBubble': '气泡对白',
    'OpenSystemBoard': '系统面板内容', 'OpenSystemFunction': '系统功能内容',
}


def diagnose_actions(value, supported, owner):
    unknown, external = [], []
    for obj in walk(value):
        if not isinstance(obj.get('Name'), str) or 'Params' not in obj:
            continue
        record = {'owner': owner, 'name': obj['Name'], 'action_id': obj.get('ActionId'),
                  'params': obj['Params']}
        if obj['Name'] not in supported:
            unknown.append(record)
        if obj['Name'] in CONTENT_CHANNELS:
            external.append({**record, 'channel': CONTENT_CHANNELS[obj['Name']]})
    return unknown, external


def scan_mainline():
    source = Snapshot()
    nodes = defaultdict(list)
    for row in source.rows('db_QuestNodeData.db', 'questnodedata'):
        nodes[int(row['Key'].split('_')[0])].append(embedded(row['BinData'])[0][1])
    handbooks = {r['QuestId']: [v for _, v in embedded(r['BinData']) if isinstance(v, list)][0]
                 for r in source.rows('db_PlotHandBook.db', 'plothandbookconfig')}
    states = {r['StateKey']: [v for _, v in embedded(r['BinData'])]
              for r in source.rows('db_flowState.db', 'flowstate')}
    result = []
    for row in source.rows('db_QuestData.db', 'questdata'):
        quest = embedded(row['BinData'])[0][1]
        if quest.get('Type') not in {1, 15}:
            continue
        task_nodes = nodes[quest['Id']]
        refs = {flow_key(o) for o in walk([quest, task_nodes])
                if o.get('FlowListName') and 'StateId' in o}
        order = [flow_key(e['Flow']) for e in handbooks.get(quest['Id'], [])
                 if e.get('Flow', {}).get('FlowListName')]
        state_objects = [o for key in set(order) | refs for o in walk(states.get(key, []))]
        # Talk-item Name is an editor label (e.g. 对话2), not an action.
        actions = Counter(o['Name'] for o in state_objects if 'Name' in o and 'Params' in o)
        unknown_task, external = [], []
        for owner, value in [('quest', quest)] + [(n['Id'], n) for n in task_nodes]:
            unknown, channels = diagnose_actions(value, TASK_EFFECTS | {'PlayFlow'}, owner)
            unknown_task.extend(unknown)
            external.extend(channels)
        unknown_flow = []
        for key in sorted(set(order) | refs):
            unknown, channels = diagnose_actions(states.get(key, []), FLOW_ACTIONS, key)
            unknown_flow.extend(unknown)
            external.extend(channels)
        types = Counter(n['Type'] for n in task_nodes)
        conditions = sorted({str(n['Condition'].get('Type')) for n in task_nodes if n.get('Condition')})
        score = 4 * len(types) + 2 * len(conditions) + len(actions)
        result.append({'quest_id': quest['Id'], 'title': resolve(quest.get('TidName', '')),
                       'type_id': quest['Type'], 'node_count': len(task_nodes), 'node_types': dict(types),
                       'conditions': conditions, 'flow_actions': dict(actions), 'score': score,
                       'recap_scene_count': len(order), 'task_only_states': sorted(refs - set(order)),
                       'recap_only_states': sorted(set(order) - refs),
                       'missing_states': sorted((refs | set(order)) - states.keys()),
                       'unsupported_task_actions': unknown_task,
                       'unsupported_flow_actions': unknown_flow,
                       'external_content_calls': external,
                       'exact_recap_coverage': bool(order) and refs == set(order) and len(order) == len(set(order))})
    result.sort(key=lambda r: (-r['score'], -r['node_count'], r['quest_id']))
    report = {'score_formula': '4 * distinct node types + 2 * distinct step conditions + distinct flow actions',
              'selection_note': 'Score is a heuristic, not a completeness proof. Prefer Type=1 with exact recap coverage.',
              'tasks': result}
    (O / '主线结构扫描.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 主线结构扫描', '', '评分：节点类型数×4 + 条件类型数×2 + 流程动作类型数。动作不计对白编辑器名称。',
             '同时扫描 Type=1 和补充 Type=15；核心案例从 Type=1 中选取。分数仅用于选样。', '',
             '| Type | ID | 名称 | 分数 | 节点 | 回顾场景 | 回顾完全覆盖 |', '|---|---|---|---:|---:|---:|---|']
    for r in result:
        lines.append(f'| {r["type_id"]} | {r["quest_id"]} | {r["title"]} | {r["score"]} | {r["node_count"]} | {r["recap_scene_count"]} | {r["exact_recap_coverage"]} |')
    (O / '主线结构扫描.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    diagnostic = ['# 主线后续机制诊断', '',
                  '静态检查一次列出全部已识别的未知动作，不在首个异常处停止。',
                  '包含未选分支；调用存在不代表默认路线一定执行。外部内容尚未提取，不能据此宣称任务完整。',
                  '未知条件、运行时排序等仍需独立验证；此报告不是全部潜在问题的穷举。', '',
                  '## 有完整回顾顺序的后续候选', '',
                  '| 任务 | 未支持任务动作 | 未支持流程动作 | 其他内容来源 |', '|---|---|---|---|']
    for r in result:
        if r['type_id'] != 1 or not r['exact_recap_coverage']:
            continue
        def names(field, key):
            return '、'.join(sorted({a[key] for a in r[field]})) or '无'
        diagnostic.append(f'| {r["quest_id"]} {r["title"]} | {names("unsupported_task_actions", "name")} | {names("unsupported_flow_actions", "name")} | {names("external_content_calls", "channel")} |')
    diagnostic += ['', '## 下一步建议', '',
                   '先以《万象新声·下》验证视频字幕、任务提示和界面调用边界；然后再检查《万象新声·上》的同类机制。',
                   '手机消息、邮件和小游戏分别建立配置关联及顺序规则，不能把这些动作统一当作无文本表现动作忽略。',
                   '《铁锈，剑与烈阳》还涉及 SetVar 与小游戏，须先确认变量和文本路线的关系。',
                   '继续保留未知角色问号，不添加任务或人物特例。', '',
                   '具体动作参数、引用 ID 和所在节点/状态见主线结构扫描.json。']
    (O / '主线后续机制诊断.md').write_text('\n'.join(diagnostic) + '\n', encoding='utf-8')
    for r in result:
        if r['type_id'] == 1 and r['exact_recap_coverage']:
            print(r['quest_id'], r['title'], r['score'], r['node_count'], r['recap_scene_count'])
    return report
