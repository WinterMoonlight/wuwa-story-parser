"""Read-only snapshot batch export with explicit coverage and failure reports."""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import re

from .database import rows, embedded, string, vec, resolve, P, O
from .export_task import Exporter, write_result, walk, PRESENTATION_ACTIONS
from .rendering import render_text
from .coverage import TASK_EFFECTS


class Snapshot:
    def __init__(self):
        self.cache = {}

    def rows(self, file, table):
        key = (file, table)
        if key not in self.cache:
            self.cache[key] = rows(file, table)
        return self.cache[key]


def safe_name(value):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(value)).rstrip('. ')
    return name[:70] or '未命名'


def chapter_info(chapter_id, chapters):
    if chapter_id not in chapters:
        return {'id': chapter_id, 'chapter': '未关联章节', 'section': '',
                'act': '', 'folder': f'未关联章节_{chapter_id}'}
    data = chapters[chapter_id]
    return {**data, 'folder': safe_name(data['chapter']) + '/' +
            safe_name(f"{chapter_id:04d}_{data['section']}_{data['act']}")}


def classify_error(message):
    rules = [
        ('topology', 'task_graph', '通用任务图：嵌套节点、并行或分支及可靠执行顺序'),
        ('success node', 'task_graph', '通用任务图：成功节点与任务结束语义'),
        ('entry/exit', 'task_actions', '任务接受、激活及结束动作的执行顺序'),
        ('success behavior', 'task_actions', '任务成功节点动作'),
        ('task action:', 'task_actions', '任务节点动作执行及其剧情触发'),
        ('task condition', 'task_conditions', '交互以外的任务完成条件与状态假设'),
        ('task step', 'task_conditions', '更多单步骤条件与入口动作'),
        ('PlotHandBook order', 'missing_order', '无回顾配置任务的可靠流程排序'),
        ('cover task flow', 'flow_coverage', '回顾流程与任务流程不一致时的归属及覆盖核验'),
        ('one explicit PlayFlow', 'multi_action', '单步骤多动作与多流程调用'),
        ('Unsupported action:', 'flow_actions', '流程动作及跨状态控制'),
        ('Conditional', 'conditions', '对话或选项条件求值'),
        ('loop', 'loops', '循环问答的终止与选择策略'),
        ('Combined', 'action_order', '对白自身动作和选项动作同时存在时的执行顺序'),
        ('JumpTalk target', 'jump_target', '跳转目标定位及跨对白组关联'),
        ('Actor change', 'actor_binding', '跨模板或场景的演员绑定'),
        ('Missing text', 'missing_text', '补齐文本引用或同版本语言资源'),
        ('No dialogue', 'no_dialogue', '纯玩法任务与无对白任务的分类'),
        ('Ambiguous', 'decode', '多内嵌数组或结构歧义的解码'),
    ]
    for fragment, code, support in rules:
        if fragment in message:
            return {'code': code, 'required_support': support}
    return {'code': 'unclassified', 'required_support': '检查原始异常与源配置，尚不能确定所缺能力'}


def observed_features(nodes):
    """Static facts, not a promise that every listed action was reached."""
    return {'node_types': sorted({str(n.get('Type', '')) for n in nodes}),
            'step_conditions': sorted({str(n.get('Condition', {}).get('Type', '')) for n in nodes if n.get('Condition')}),
            'task_action_names': sorted({o['Name'] for o in walk(nodes) if isinstance(o.get('Name'), str)}),
            'unsupported_task_actions': sorted({o['Name'] for o in walk(nodes)
                                                if isinstance(o.get('Name'), str) and o['Name'] not in TASK_EFFECTS | {'PlayFlow'}})}


def export_mainline():
    source = Snapshot()
    chapters = {}
    for row in source.rows('db_quest_chapter.db', 'questchapter'):
        values = [render_text(resolve(string(row['BinData'], i))) for i in range(1, 5)]
        chapters[row['Id']] = dict(zip(('chapter', 'section', 'act', 'chapter_title'), values), id=row['Id'])
    tree = defaultdict(list)
    for row in source.rows('db_QuestTree.db', 'questtreenode'):
        for qid in vec(row['BinData'], 2):
            tree[qid].append({'node_id': row['Id'], 'tree_chapter_id': row['ChapterId']})
    nodes = defaultdict(list)
    for row in source.rows('db_QuestNodeData.db', 'questnodedata'):
        nodes[int(row['Key'].split('_')[0])].append(embedded(row['BinData'])[0][1])
    quests = [embedded(r['BinData'])[0][1] for r in source.rows('db_QuestData.db', 'questdata')]
    selected = sorted((q for q in quests if q.get('Type') in {1, 15}),
                      key=lambda q: (q['Type'], q.get('ChapterId', 99999), q['Id']))
    # A new run prevents old successes from being mistaken for this run's results.
    root = O / '主线批量' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    root.mkdir(parents=True)
    records = []
    for index, quest in enumerate(selected, 1):
        qid = quest['Id']
        chapter = chapter_info(quest.get('ChapterId'), chapters)
        record = {'quest_id': qid, 'title': render_text(resolve(quest.get('TidName', ''))) or '未命名',
                  'type_id': quest['Type'], 'chapter': chapter,
                  'quest_tree_memberships': tree[qid], 'features': observed_features(nodes[qid])}
        group = '主线_Type1' if quest['Type'] == 1 else '补充潮汐任务_Type15'
        try:
            result = Exporter(source=source).export(qid)
            if result['validation']['missing_text_ids']:
                raise ValueError('Missing text references: ' + repr(result['validation']['missing_text_ids']))
            if not result['events']:
                raise ValueError('No dialogue events in selected route')
            result['classification'] = {'type_id': quest['Type'], 'chapter': chapter,
                                        'quest_tree_memberships': tree[qid]}
            files = write_result(result, root / group / chapter['folder'], quiet=True)
            record.update(status='exported', files=[str(p.relative_to(root)).replace('\\', '/') for p in files],
                          event_count=len(result['events']), choices=len(result['route']['choices']),
                          validation=result['validation'])
        except Exception as exc:
            message = str(exc) or type(exc).__name__
            record.update(status='unsupported', error_type=type(exc).__name__, error=message,
                          **classify_error(message))
            # Partial parser events never become a completed task file.
        records.append(record)
        if index % 10 == 0 or index == len(selected):
            print(f'Processed {index}/{len(selected)}; exported {sum(r["status"] == "exported" for r in records)}', flush=True)
    failures = [r for r in records if r['status'] != 'exported']
    counts = {str(t): {status: sum(r['status'] == status and r['type_id'] == t for r in records)
                      for status in ('exported', 'unsupported')} for t in (1, 15)}
    snapshot_files = {}
    for file in ['db_QuestData.db', 'db_QuestNodeData.db', 'db_QuestTree.db', 'db_quest_chapter.db',
                 'db_PlotHandBook.db', 'db_flowState.db', 'db_speaker.db', 'zh-Hans/lang_speaker.db',
                 'zh-Hans/lang_multi_text.db', 'zh-Hans/lang_multi_text_1sthalf.db']:
        snapshot_files[file] = hashlib.sha256((P / file).read_bytes()).hexdigest()
    report = {'scope': 'All local QuestData Type=1 plus separately grouped Type=15; not a released-content whitelist',
              'ordering': 'Chapter configuration grouping; quest ID sorting is for filing only, not story chronology',
              'counts_by_type': counts, 'source_sha256': snapshot_files,
              'build_info': (P / 'Misc/BuildInfo.txt').read_text(encoding='utf-8-sig'),
              'records': records}
    (root / '导出清单.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (root / '暂不支持任务.json').write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 主线批量导出报告', '',
             '| 范围 | 成功 | 暂不支持 |', '|---|---:|---:|',
             *[f'| Type={t} | {counts[str(t)]["exported"]} | {counts[str(t)]["unsupported"]} |' for t in (1, 15)], '',
             'Type=1 为主线候选；同样标注潮汐任务的 Type=15 单列补充。保留所有 ID，不按同名去重。',
             '本地配置可能包含旧版、测试或未开放任务；并不代表全部正式上线内容。',
             '目录按 quest_chapter 的章/幕归类。文件名 ID 不代表剧情顺序；任务间前后顺序尚未还原。',
             '成功项仅为当前支持范围内的单路线，不含环境对白与未选分支。女性分支，玩家名为漂泊者。',
             '', '## 已导出任务', '']
    for r in records:
        if r['status'] == 'exported':
            lines.append(f'- {r["quest_id"]} {r["title"]}（Type={r["type_id"]}）：{r["event_count"]} 个事件，{r["choices"]} 次选择；[TXT](<{r["files"][1]}>) / [JSON](<{r["files"][0]}>)')
    lines += ['', '## 所缺能力（按首次阻塞原因统计）', '']
    for code, count in Counter(r['code'] for r in failures).most_common():
        example = next(r for r in failures if r['code'] == code)
        lines.append(f'- {code}：{count} 个任务。{example["required_support"]}。')
    lines += ['', '这是首次失败位置，不是每个任务的全部障碍；JSON 同时记录节点类型、条件与任务动作供后续排查。', '',
              '### 静态配置中出现的复杂结构', '',
              '以下为失败任务中的出现次数，单任务每项只计一次，不表示选中路线一定经过该结构。', '']
    for field, label in [('node_types', '任务节点'), ('step_conditions', '步骤条件'),
                         ('unsupported_task_actions', '当前回顾导出器未接受的任务动作')]:
        observed = Counter(value for r in failures for value in r['features'][field])
        lines.append(f'- {label}：' + '、'.join(f'{name}（{count}）' for name, count in observed.most_common(15)))
    lines += ['', '已有精确回顾顺序时可校验复杂父子结构并生成阅读路线，尚未实现通用任务图运行时。优先补充未知动作、回顾差异与无回顾排序；',
              '其次是变量、战斗、区域、副本等条件假设，以及任务动作中的 PlayFlow 调度。',
              '任务动作中的 PlayFlow 只有在其显式引用被回顾顺序完全覆盖时才接受；这不代表执行了任务动作。',
              '后续仍需核验跨状态控制、循环、缺失引用与任务间前后顺序。', '',
              '## 暂未导出任务', '', '| Type | 任务 ID | 任务名 | 章/幕 | 需补充支持 | 首次失败原因 |', '|---|---|---|---|---|---|']
    for r in failures:
        cells = [r['type_id'], r['quest_id'], r['title'], r['chapter']['folder'], r['required_support'], r['error']]
        lines.append('| ' + ' | '.join(str(c).replace('|', '\\|').replace('\n', ' ') for c in cells) + ' |')
    (root / '导出报告.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(root)
    print(counts)
    return root, report
