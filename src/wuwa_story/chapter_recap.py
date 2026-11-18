"""Place already extracted task fragments using a chapter-wide recap."""
from collections import Counter, defaultdict
from hashlib import sha256
from sqlite3 import OperationalError
import struct

from .database import embedded, vec
from .dependency_positions import _sync_flow, dependency_positions
from .export_task import walk
from .task_condition_flows import _female_projection
from .task_flows import classify_task_flows


def _prequest(quest, quest_id):
    return quest.get('ProvideType') == {'Conditions': [{'Type': 'PreQuest', 'PreQuest': quest_id}]}


def _original_tasks(row):
    try:
        originals = vec(row['BinData'], 1)
        replays = vec(row['BinData'], 2)
    except (struct.error, ValueError):
        return []
    if (len(originals) < 2 or len(originals) != len(replays)
            or len(set(originals + replays)) != len(originals + replays)
            or any(task_id <= 0 for task_id in originals + replays)):
        return []
    return originals


def _entry_flow(entry):
    return _sync_flow({'Name': 'PlayFlow', 'Params': entry.get('Flow')})


def _task_window(entries, task_ids, qid, tip_owners, flow_owners=None):
    starts = {}
    seen = []
    anchors = []
    for index, entry in enumerate(entries):
        owners = tip_owners.get(entry.get('TidTip'), set())
        if len(owners) > 1:
            return None
        if not owners:
            continue
        owner = next(iter(owners))
        if not seen or seen[-1] != owner:
            seen.append(owner)
            starts[owner] = index
        if owner == qid:
            anchors.append(index)
    if seen != task_ids:
        return None
    if flow_owners:
        flow_keys = [_entry_flow(entry) for entry in entries]
        counts = Counter(flow_keys)
        for owner, first_tip in starts.items():
            start = first_tip
            while start:
                previous = entries[start - 1]
                key = flow_keys[start - 1]
                if (previous.get('TidTip') or previous.get('IsHideUi') or key is None
                        or counts[key] != 1 or flow_owners.get(key) != {owner}):
                    break
                start -= 1
            starts[owner] = start
    task_index = task_ids.index(qid)
    end = starts[task_ids[task_index + 1]] if task_index + 1 < len(task_ids) else len(entries)
    return starts[qid], end, anchors


def _place_groups(entries, start, end, groups, edges):
    flow_entries = {}
    for index in range(start, end):
        flow = entries[index].get('Flow', {})
        if not flow.get('FlowListName'):
            continue
        key = _entry_flow(entries[index])
        if key is None or key in flow_entries:
            return None
        flow_entries[key] = index
    checks = dependency_positions(edges, list(flow_entries))
    if checks['conflicts']:
        return None

    counts = Counter(segment['state_key'] for group in groups for segment in group['segments'])
    flow_positions = {index: position for position, index in enumerate(flow_entries.values())}
    placements = {}
    for group_index, group in enumerate(groups):
        if not group.get('local_order_verified') or group.get('intermediate_content'):
            continue
        keys = [segment['state_key'] for segment in group['segments']]
        if not keys or any(counts[key] != 1 or key not in flow_entries for key in keys):
            continue
        positions = [flow_entries[key] for key in keys]
        ordinal_positions = [flow_positions[position] for position in positions]
        if ordinal_positions != list(range(ordinal_positions[0], ordinal_positions[0] + len(keys))):
            continue
        placements.update((position, (group_index, index)) for index, position in enumerate(positions))
    if len(placements) < 2:
        return None
    return flow_entries, placements, checks


def recover_chapter_recap(quest, nodes, groups, coverage, source, *, states=None, choices=None):
    qid = quest['Id']
    if quest.get('Type') != 1 or quest.get('ChapterId') is None or not groups:
        return None
    try:
        recall_rows = source.rows('db_QuestRecall.db', 'recallconfig')
    except OperationalError:
        return None
    recalls = [(row, _original_tasks(row)) for row in recall_rows]
    matches = [(row, ids) for row, ids in recalls if qid in ids]
    if len(matches) != 1:
        return None
    recall, task_ids = matches[0]
    last = task_ids[-1]

    quests = defaultdict(list)
    for row in source.rows('db_QuestData.db', 'questdata'):
        for _, definition in embedded(row['BinData']):
            if isinstance(definition, dict) and definition.get('Id') == row['QuestId']:
                quests[row['QuestId']].append(definition)
    if any(len(quests[task_id]) != 1 for task_id in task_ids):
        return None
    originals = [quests[task_id][0] for task_id in task_ids]
    if any((q.get('Type'), q.get('ChapterId'), q.get('DungeonId')) !=
           (1, quest['ChapterId'], quest.get('DungeonId')) for q in originals):
        return None
    if any(not _prequest(q, previous) for previous, q in zip(task_ids, originals[1:])):
        return None

    tip_owners, flow_owners = defaultdict(set), defaultdict(set)
    for row in source.rows('db_QuestNodeData.db', 'questnodedata'):
        owner = int(row['Key'].split('_', 1)[0])
        if owner in task_ids:
            node = embedded(row['BinData'])[0][1]
            tip = node.get('TidTip')
            if tip:
                tip_owners[tip].add(owner)
            for reference in walk(node):
                if 'FlowListName' in reference:
                    key = _sync_flow({'Name': 'PlayFlow', 'Params': reference})
                    if key:
                        flow_owners[key].add(owner)

    books = defaultdict(list)
    for row in source.rows('db_PlotHandBook.db', 'plothandbookconfig'):
        books[row['QuestId']].append(row)
    candidates = []
    for owner, rows in books.items():
        definitions = quests.get(owner, [])
        if owner in task_ids or len(rows) != 1 or len(definitions) != 1:
            continue
        candidate = definitions[0]
        if (candidate.get('Type') != 1 or candidate.get('DungeonId') != quest.get('DungeonId')
                or candidate.get('Reference') != [f'q_{last}'] or not _prequest(candidate, last)):
            continue
        book = rows[0]
        lists = [v for _, v in embedded(book['BinData']) if isinstance(v, list)]
        if len(lists) != 1 or not all(isinstance(e, dict) for e in lists[0]):
            continue
        entries = lists[0]
        window = _task_window(entries, task_ids, qid, tip_owners, flow_owners)
        if window:
            candidates.append((book, entries, window))
    if len(candidates) != 1:
        return None

    book, entries, (start, end, anchors) = candidates[0]
    placements = _place_groups(entries, start, end, groups, coverage['order']['dependencies']['edges'])
    if placements is None:
        return None
    flow_entries, placed, checks = placements
    covered_groups = {group for group, _ in placed.values()}
    projected_nodes, _, rejected = _female_projection(nodes)
    occurrences = classify_task_flows(quest, projected_nodes)
    restored = {}
    if states is not None and book['QuestId'] == 125900000:
        from .reading_cases.chapter_recap_dialogue import restore_dialogue
        restored = restore_dialogue(qid, projected_nodes, occurrences, entries, flow_entries,
                                    placed, states, source, choices)
    outside_recap = sorted(key for key in occurrences if key not in flow_entries
                           and any(item['kind'] != 'failure_branch' for item in occurrences[key]))
    gameplay_outside_recap = any(g['status'] == 'local_order_only'
                                 for g in coverage.get('levelplay_local_sequences', []))
    covers_task_groups = len(covered_groups) == len(groups)
    return {
        'recap_quest_id': book['QuestId'], 'recall_id': recall['RecallId'],
        'original_task_ids': task_ids, 'recall_sha256': sha256(recall['BinData']).hexdigest(),
        'handbook_sha256': sha256(book['BinData']).hexdigest(),
        'start_entry_index': start, 'end_entry_index_exclusive': end,
        'next_task_tip': next((entry['TidTip'] for entry in entries[end:]
                              if entry.get('TidTip')), None),
        'anchors': [{'entry_index': i, 'text_id': entries[i]['TidTip']} for i in anchors],
        'flow_entries': [
            {'entry_index': index, 'state_key': key, 'source_entry': entries[index],
             'local_segment': list(placed[index]) if index in placed else None,
             **({'recap_segment': restored[index]} if index in restored else {})}
            for key, index in flow_entries.items()],
        'unplaced_group_indices': [i for i in range(len(groups)) if i not in covered_groups],
        'task_states_outside_recap': outside_recap,
        'unresolved_gender_selectors': rejected,
        'gameplay_outside_recap': gameplay_outside_recap,
        'covers_task_groups': covers_task_groups,
        'covers_all_reading_groups': covers_task_groups and not gameplay_outside_recap,
        'has_gaps': len(placed) + len(restored) != len(flow_entries) or bool(outside_recap or rejected)
                    or gameplay_outside_recap,
        'task_dependency_check': checks, 'runtime_order_verified': False,
    }
