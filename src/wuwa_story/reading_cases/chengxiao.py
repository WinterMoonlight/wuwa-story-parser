"""Restore the final seal's dialogue in the chapter-wide recap."""
from sqlite3 import OperationalError

from ..chapter_recap import _original_tasks, _prequest
from ..counter_order import counter_sequences
from ..database import embedded
from ..declared_levelplay import declared_levelplays
from ..dependency_positions import _sync_flow
from ..export_task import flow_key
from ..terminal_text import synchronous


QUEST_ID = 125900000
OWNER = 146000002
LEVELPLAY = 146000053
FAMILY = '剧情_1_1_乘宵山主线_眠龙庭_'
WATER = FAMILY + '1_5'
SEAL = FAMILY + '1_13'
ARCHIVE = FAMILY + '1_16'
COUNTER_FLOWS = [FAMILY + suffix for suffix in ('1_9', '1_4', '1_13')]


def add_final_seal_dialogue(quest, backbone, states, source, choices=None):
    if quest.get('Id') != QUEST_ID or quest.get('Type') != 1:
        return
    segments = backbone['segments']
    anchors = [s for s in segments if s['state_key'] in (WATER, ARCHIVE)]
    if ([s['state_key'] for s in anchors] != [WATER, ARCHIVE]
            or any(s['status'] != 'parsed' for s in anchors)
            or any(s['state_key'] == SEAL for s in segments)):
        return
    before, after = anchors
    if 'current_task_continuation' in before or segments[segments.index(before) + 1] is not after:
        return

    try:
        recall_rows = source.rows('db_QuestRecall.db', 'recallconfig')
    except OperationalError:
        return
    recalls = [(row, original_ids) for row in recall_rows
               if OWNER in (original_ids := _original_tasks(row))]
    if len(recalls) != 1:
        return
    recall, originals = recalls[0]
    last = originals[-1]
    if quest.get('Reference') != [f'q_{last}'] or not _prequest(quest, last):
        return
    owners = [v for row in source.rows('db_QuestData.db', 'questdata') if row['QuestId'] == OWNER
              for _, v in embedded(row['BinData']) if isinstance(v, dict) and v.get('Id') == OWNER]
    if (len(owners) != 1 or owners[0].get('Type') != 1
            or owners[0].get('DungeonId') != quest.get('DungeonId')):
        return
    owner = owners[0]
    nodes = [embedded(row['BinData'])[0][1] for row in source.rows('db_QuestNodeData.db', 'questnodedata')
             if row['Key'].startswith(f'{OWNER}_')]
    by_id = {n['Id']: n for n in nodes}
    if len(by_id) != len(nodes) or not {6, 8, 9, 13, 49} <= by_id.keys():
        return
    enable = [a for a in by_id[13].get('EnterActions', []) if synchronous(a, 'EnableLevelPlay')
              and a.get('Params') == {'Configs': [{'LevelPlayId': LEVELPLAY, 'Enable': True}]}]
    if (len(enable) != 1
            or not any(a.get('Name') == 'PlayFlow' and flow_key(a['Params']) == WATER
                       for a in by_id[9].get('FinishActions', []))
            or not any(_sync_flow(a) == ARCHIVE for a in by_id[49].get('FinishActions', []))):
        return

    entries = backbone['order_source']['entries']
    tip_nodes = [by_id[i] for i in (6, 8, 49)]
    pairs = [(n['Id'], n.get('TidTip')) for n in tip_nodes]
    if not all(tip for _, tip in pairs):
        return
    indices = [[i for i, e in enumerate(entries) if e.get('TidTip') == tip] for _, tip in pairs]
    end = after['entry_index']
    if (indices != [[end - 3], [end - 2], [end - 1]]
            or end - 3 <= before['entry_index']
            or any(e.get('Flow', {}).get('FlowListName') for e in entries[before['entry_index'] + 1:end])):
        return

    links, _, audits = declared_levelplays(owner, nodes, entries, source)
    counters = [g for g in counter_sequences(audits, links, states, source, set(COUNTER_FLOWS), choices)
                if g['levelplay_id'] == LEVELPLAY and g['state_keys'] == COUNTER_FLOWS]
    if len(counters) != 1:
        return
    counter = counters[0]
    proof = counter['proof']
    threshold = proof['thresholds'][-1]
    if (proof['variable']['Name'] != 'n1'
            or [gate['threshold'] for gate in proof['thresholds']] != [1, 2, 3]
            or sorted((w['node_id'], w['increment']) for w in proof['positive_writes']) != [(7, 1), (8, 1), (9, 1)]
            or threshold['node_id'] != 12):
        return
    parsed = counter['segments'][-1]
    expected_keys = [f'Chengxiaoshan_main_1_1_372_{i}' for i in (1, 2, 3)]
    if (parsed['missing_text_ids'] or parsed['unverified_content']
            or any(e['kind'] != 'dialogue' for e in parsed['events'])
            or [e['text_id'] for e in parsed['events']] != expected_keys):
        return
    before['current_task_continuation'] = {
        **parsed, 'order_scope': 'mianlong_court_final_seal_recap_stage',
        'scene_title': '【眠龙庭 · 曜岩计数达到三次】',
        'placement': {
            'owner_quest_id': OWNER, 'recall_id': recall['RecallId'], 'levelplay_id': LEVELPLAY,
            'after_state': WATER, 'before_state': ARCHIVE,
            'recap_tips': [{'entry_index': i[0], 'node_id': n, 'text_id': tip}
                           for i, (n, tip) in zip(indices, pairs)],
            'enable_action': enable[0], 'counter': proof, 'selected_threshold': threshold,
            'basis': 'owned counter-triggered dialogue and exact seal, return and archive recap hints',
            'dialogue_completion_order_verified': False, 'runtime_verified': False,
        },
    }
