"""Generate a chapter index without rewriting any dialogue exports."""
from collections import Counter, defaultdict
from graphlib import CycleError, TopologicalSorter
from hashlib import sha256
import json
from pathlib import Path

from .database import P, integer, rows, vec


INDEX_NAME = '主线连读索引.md'
EVENT_CHAPTER_ID = 3001


def _load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def _prerequisite(definition):
    provide = definition.get('ProvideType', {})
    conditions = provide.get('Conditions', [])
    dependencies = [c for c in conditions if c.get('Type') in {'PreQuest', 'PreChildQuest'}]
    if (provide.get('Type') not in (None, 0) or len(dependencies) != 1
            or any(c.get('Type') not in {'PreQuest', 'PreChildQuest', 'ExploreLevel', 'OpenDate'}
                   for c in conditions)):
        return None, None
    condition = dependencies[0]
    if condition['Type'] == 'PreQuest':
        return condition['PreQuest'], None
    child = condition['PreChildQuest']
    return child['QuestId'], child['ChildQuestId']


def _reachable(graph, start):
    seen, pending = set(), list(graph[start])
    while pending:
        previous = pending.pop()
        if previous not in seen:
            seen.add(previous)
            pending.extend(graph[previous])
    return seen


def _order(graph):
    ordered = []
    sorter = TopologicalSorter({q: sorted(graph[q]) for q in sorted(graph)})
    try:
        sorter.prepare()
    except CycleError:
        return sorted(graph), set(graph), True
    while sorter.is_active():
        ready = sorted(sorter.get_ready())
        ordered.extend(ready)
        sorter.done(*ready)
    before = {q: _reachable(graph, q) for q in ordered}
    uncertain = {q for q in ordered if any(q != other and other not in before[q] and q not in before[other]
                                         for other in ordered)}
    return ordered, uncertain, False


def _chapter_tree_edges(tree_rows, chapter_of):
    chapters, next_nodes, previous_nodes = {}, {}, {}
    for row in tree_rows:
        blob = row['BinData']
        node = row['Id']
        chapter_ids = {chapter_of[qid] for qid in vec(blob, 2) if qid in chapter_of}
        if len(chapter_ids) == 1:
            chapters[node] = next(iter(chapter_ids))
            next_nodes[node] = integer(blob, 10)
            previous_nodes[node] = vec(blob, 9)
    return sorted({(chapters[node], chapters[target]) for node, target in next_nodes.items()
                   if target in chapters and node in previous_nodes[target]
                   and chapters[node] != chapters[target]})


def _task_links(task, repeat_title=False):
    json_file, txt_file = task['files']
    name = task['title']
    label = f' · `{task["quest_id"]}`' if repeat_title else ''
    return f'[{name}](<{txt_file}>){label} · [JSON](<{json_file}>)'


def _task_list(ids, tasks, uncertain):
    repeats = Counter(tasks[q]['title'] for q in ids)
    return [f'{"-" if q in uncertain else "1."} {_task_links(tasks[q], repeats[tasks[q]["title"]] > 1)}'
            + (' · **顺序待核**' if q in uncertain else '') for q in ids]


def write_chapter_reading_index(root, report, tree_rows):
    root = Path(root)
    tasks = {task['quest_id']: task for task in report['tasks'] if task['type_id'] == 1}
    chapters, chapter_tasks, prerequisites, child_nodes = {}, defaultdict(set), {}, {}
    for qid, task in tasks.items():
        document = _load(root / task['files'][0])
        chapter = document['classification']['chapter']
        chapters[chapter['id']] = chapter
        chapter_tasks[chapter['id']].add(qid)
        prerequisites[qid] = _prerequisite(document['source']['quest_definition'])
        child_nodes[qid] = {node['Id'] for node in document['source']['task_nodes']
                            if node.get('Type') == 'ChildQuest'}

    all_chapter_ids = {qid: cid for cid, ids in chapter_tasks.items() for qid in ids}
    chapter_of = {qid: cid for qid, cid in all_chapter_ids.items() if cid not in (None, EVENT_CHAPTER_ID)}
    chapter_graph = {cid: set() for cid in set(chapter_of.values())}
    chapter_notes = defaultdict(list)
    task_graph = {qid: set() for qid in tasks}
    for qid, (previous, child) in prerequisites.items():
        if previous not in tasks or (child is not None and child not in child_nodes[previous]):
            continue
        if all_chapter_ids[previous] == all_chapter_ids[qid]:
            task_graph[qid].add(previous)
        if qid in chapter_of and previous in chapter_of and chapter_of[qid] != chapter_of[previous]:
            cid, predecessor = chapter_of[qid], chapter_of[previous]
            chapter_graph[cid].add(predecessor)
            if child is not None:
                chapter_notes[cid].append(
                    f'《{tasks[qid]["title"]}》的前置是上一幕任务 `{previous}` 的子任务 `{child}`。')

    recap_orders = report.get('chapter_task_orders', {})
    chapter_recaps = defaultdict(list)
    for recap_id, ids in recap_orders.items():
        if len(ids) < 2 or not all(qid in chapter_of for qid in ids):
            continue
        cid = chapter_of[ids[0]]
        if all(chapter_of[qid] == cid for qid in ids):
            for previous, qid in zip(ids, ids[1:]):
                task_graph[qid].add(previous)
            if int(recap_id) in chapter_tasks.get(None, set()):
                chapter_recaps[cid].append(int(recap_id))

    for previous, cid in _chapter_tree_edges(tree_rows, chapter_of):
        if previous in _reachable(chapter_graph, cid) or cid in _reachable(chapter_graph, previous):
            continue
        earlier = '、'.join(f'《{chapters[dep]["act"]}》' for dep in sorted(chapter_graph[cid]))
        chapter_graph[cid].add(previous)
        chapter_notes[cid].append(
            f'章节树把这一幕接在《{chapters[previous]["act"]}》之后。'
            + (f'任务前置指向{earlier}。' if earlier else '')
            + '两幕的实际开启先后待核。')

    ordered, uncertain, conflict = _order(chapter_graph)
    lines = ['# 主线连读索引', '',
             f'从序幕开始，覆盖 {len(ordered)} 幕的 {len(chapter_of)} 个主线任务。'
             '点击任务名打开 TXT 阅读稿，JSON 保留来源和触发信息。', '',
             '同幕顺序依据任务前置条件和已核对的章节回顾。遇到并行解锁时，沿用章节树的阅读连接，'
             '并标出实际先后待核的位置。', '']
    if conflict:
        lines.extend(['章节依赖存在冲突，下列章节位置待核。', ''])
    region = None
    for cid in ordered:
        chapter = chapters[cid]
        if chapter['chapter'] != region:
            region = chapter['chapter']
            lines.extend([f'## {region}', ''])
        subtitle = f'{chapter["section"]} · {chapter["act"]}'
        lines.extend([f'### {subtitle}' + ('（与其他幕先后待核）' if cid in uncertain else ''), ''])
        for note in chapter_notes[cid]:
            lines.extend([note, ''])
        ids, pending, _ = _order({q: task_graph[q] for q in chapter_tasks[cid]})
        lines.extend(_task_list(ids, tasks, pending) + [''])
        for recap_id in chapter_recaps[cid]:
            lines.extend([f'总回顾入口 · {_task_links(tasks[recap_id])}', ''])

    if EVENT_CHAPTER_ID in chapter_tasks:
        lines.extend(['## 追月节', '', '以下活动任务可按前置关系连读，与各幕之间的插入位置待核。', ''])
        ids, pending, _ = _order({q: task_graph[q] for q in chapter_tasks[EVENT_CHAPTER_ID]})
        lines.extend(_task_list(ids, tasks, pending) + [''])
    linked_recaps = {qid for ids in chapter_recaps.values() for qid in ids}
    unplaced = sorted(chapter_tasks.get(None, set()) - linked_recaps)
    if unplaced:
        lines.extend(['## 章节位置待核', '', *_task_list(unplaced, tasks, set(unplaced)), ''])
    path = root / INDEX_NAME
    path.write_text('\n'.join(lines), encoding='utf-8')
    return path


def export_existing_index(root):
    root = Path(root)
    database = 'db_QuestTree.db'
    expected = _load(root / '覆盖报告.json')['source_sha256'][database]
    tree_rows = rows(database, 'questtreenode') if sha256((P / database).read_bytes()).hexdigest() == expected else []
    return write_chapter_reading_index(root, _load(root / '主线阅读报告.json'), tree_rows)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='为指定的覆盖阅读版生成主线连读索引')
    parser.add_argument('batch', type=Path)
    print(export_existing_index(parser.parse_args().batch))
