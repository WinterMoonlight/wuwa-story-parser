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
    'Combined item/option actions need ordering verification': ('combined_interaction', '界面调用与选项的关系、控制影响及正文归属'),
}


def collect_blockers(result, files):
    cases = []
    for s in (result.get('recap_backbone') or {}).get('segments', []):
        if s['status'] != 'blocked':
            continue
        error = s.get('error', '')
        category, need = RULES.get(error, ('unclassified', '核查该原始错误及对应配置，不能凭错误名称推断执行语义'))
        cases.append({'quest_id': result['quest_id'], 'title': result['title'],
            'entry_index': s['entry_index'], 'state_key': s['state_key'], 'error': error,
            'category': category, 'evidence_needed': need, 'status': 'blocked',
            'prefix_event_count': s.get('prefix_event_count', 0),
            'control_boundary': s.get('control_boundary'), 'source_sha256': s.get('sha256'),
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


def write_report(cases, root):
    report = build_report(cases)
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
    (root/'剩余阻塞.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return report
