"""Actionable recap blockers, counted by occurrence and exact source identity."""
import json
from collections import Counter


RULES = {
    'Missing flow state': ('missing_flow', '同版本精确StateKey对应的流程定义，或明确别名/替代引用证据'),
    'QTE runtime outcome evaluator is unsupported': ('qte', '结果映射及可证明的控制路径；不能猜实际成功/失败'),
    'Unsupported action: PlaySequenceData': ('sequence_call', '回调及正文来源证据；资产暂后置，不靠演出占位减少阻塞'),
    'Unsupported action: SetVar': ('state_control', '赋值后控制边界与执行语义；已有前缀不代表整段完成'),
    'Unsupported action: FinishState': ('state_control', '状态结束影响及调用栈边界；不能直接当FinishTalk'),
    'Unsupported action: CalculateVar': ('variable_state', '实际可用初值、作用域及计算语义；实体默认值不等于回顾当前值'),
    'Conditional menu availability is unknown': ('variable_state', '进入菜单时各条件变量的当前值；后续CalculateVar与实体动作仍需核验'),
    'Combined item/option actions need ordering verification': ('combined_interaction', '界面调用与选项的关系、控制影响及正文归属'),
}


def collect_blockers(result, files):
    from .task_flows import classify_task_flows
    cases = []
    source = result.get('source', {})
    occurrences = classify_task_flows(source.get('quest_definition', {}), source.get('task_nodes', []))
    segments = (result.get('recap_backbone') or {}).get('segments', [])
    def anchor(segment):
        return {'entry_index': segment['entry_index'], 'state_key': segment['state_key'], 'status': segment['status']}
    for index, s in enumerate(segments):
        if s['status'] != 'blocked':
            continue
        error = s.get('error', '')
        category, need = RULES.get(error, ('unclassified', '核查该原始错误及对应配置，不能凭错误名称推断执行语义'))
        cases.append({'quest_id': result['quest_id'], 'title': result['title'],
            'entry_index': s['entry_index'], 'state_key': s['state_key'], 'error': error,
            'category': category, 'evidence_needed': need, 'status': 'blocked',
            'prefix_event_count': s.get('prefix_event_count', 0),
            'control_boundary': s.get('control_boundary'), 'source_sha256': s.get('sha256'),
            'task_call_sites': occurrences.get(s['state_key'], []),
            'previous_recap_flow': anchor(segments[index - 1]) if index else None,
            'next_recap_flow': anchor(segments[index + 1]) if index + 1 < len(segments) else None,
            'recap_neighbors_establish_runtime_order': False,
            'files': list(files)})
    return cases


def build_report(cases):
    groups = {}
    for case in cases:
        key = (case['category'], case['state_key'], case['error'])
        groups.setdefault(key, []).append(case)
    return {'scope': 'recap blockers only; not all task/runtime or asset gaps',
        'summary': {'tasks': len({c['quest_id'] for c in cases}), 'occurrences': len(cases),
            'unique_exact_blockers': len(groups), 'categories_by_occurrence': dict(Counter(c['category'] for c in cases)),
            'prefix_segments_still_blocked': sum(bool(c['prefix_event_count']) for c in cases),
            'prefix_events_still_blocked': sum(c['prefix_event_count'] for c in cases)},
        'groups': [{'category': key[0], 'state_key': key[1], 'error': key[2],
                    'occurrences': len(values), 'quest_ids': sorted({v['quest_id'] for v in values}),
                    'evidence_needed': values[0]['evidence_needed']} for key, values in sorted(groups.items())],
        'cases': cases}


def collect_unresolved_choices(result, files):
    cases = []
    for segment in (result.get('recap_backbone') or {}).get('segments', []):
        for entry in segment.get('unverified_content', []):
            if entry.get('kind') == 'implicit_choice_retry':
                cases.append({'quest_id': result['quest_id'], 'title': result['title'],
                              'entry_index': segment['entry_index'], 'state_key': segment['state_key'],
                              'status': 'original_choice_still_unsupported', 'evidence': entry,
                              'files': list(files)})
    return cases


def write_report(cases, root, unresolved_choices=None):
    report = build_report(cases)
    report['unresolved_original_choices'] = list(unresolved_choices or [])
    (root/'剩余阻塞.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    s = report['summary']
    lines = ['# 剩余回顾阻塞', '',
        f"{s['tasks']}任务、{s['occurrences']}次阻塞；按错误和精确流程键去重为{s['unique_exact_blockers']}项。",
        f"其中{s['prefix_segments_still_blocked']}段有{s['prefix_events_still_blocked']}个前缀事件，仍计阻塞。",
        '仅覆盖回顾解析阻塞，不代表全部任务、运行时和资产缺口。', '',
        '|任务/回顾索引|流程|原错误|前缀事件|所需证据|JSON|', '|---|---|---|---:|---|---|']
    clean = lambda v: str(v).replace('|', '\\|').replace('\n', ' ')
    for c in cases:
        lines.append('|'+ '|'.join([clean(f"{c['quest_id']} {c['title']} / {c['entry_index']}"),
            clean(c['state_key']), clean(c['error']), str(c['prefix_event_count']), clean(c['evidence_needed']),
            f"[来源](<{c['files'][0]}>)"])+'|')
    if unresolved_choices:
        lines.extend(['', '## 原选项仍未支持', '',
                      '以下区段已采用完整可解析的无条件备选，原选项的控制错误继续保留。', ''])
        for case in unresolved_choices:
            entry = case['evidence']
            lines.append(f"- {case['quest_id']} {case['title']} / {case['state_key']}，"
                         f"原选项{entry['original_selected_index']}仍为{entry['original_error']}，本版选项{entry['selected_index']}。")
    (root/'剩余阻塞.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return report
