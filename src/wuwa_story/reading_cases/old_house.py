"""Place Yangyang's awakening inside the old-house dungeon."""
from ..dependency_positions import _sync_flow
from ..export_task import walk
from ..task_flows import classify_task_flows
from ..task_local_order import _flow_segment
from ..terminal_text import synchronous


QUEST_ID = 189000005
DUNGEON_ID = 2525
FAMILY = '剧情_3_5_玄方城_秧秧_2_'
FAINT = FAMILY + '1_2'
AWAKENING = FAMILY + '4_1'
AFTER_EXIT = FAMILY + '1_10'
EXIT_TIP = 'Quest_189000005_ChildQuestTip_317_70'


def add_old_house_awakening(quest, nodes, backbone, states, source, choices=None):
    if quest.get('Id') != QUEST_ID or quest.get('Type') != 1:
        return
    segments = backbone['segments']
    anchors = [s for s in segments if s['state_key'] in (FAINT, AFTER_EXIT)]
    if ([s['state_key'] for s in anchors] != [FAINT, AFTER_EXIT]
            or any(s['status'] != 'parsed' for s in anchors)
            or any(s['state_key'] == AWAKENING for s in segments)):
        return
    before, after = anchors
    if 'current_task_continuation' in before or segments[segments.index(before) + 1] is not after:
        return
    entries = backbone['order_source']['entries']
    tips = [i for i, entry in enumerate(entries) if entry.get('TidTip') == EXIT_TIP]
    tip_index = before['entry_index'] + 1
    if tips != [tip_index] or after['entry_index'] != tip_index + 1:
        return

    by_id = {node['Id']: node for node in nodes}
    expected_nodes = {
        1: ('Sequence', 0), 2: ('Sequence', 1), 12: ('ChildQuest', 2),
        129: ('Sequence', 2), 133: ('ChildQuest', 158), 135: ('ChildQuest', 129),
        158: ('ParallelSelect', 129), 168: ('Sequence', 2), 203: ('Action', 168),
    }
    if (len(by_id) != len(nodes) or not expected_nodes.keys() <= by_id.keys()
            or any((by_id[i].get('Type'), by_id[i].get('ParentNodeId')) != shape
                   for i, shape in expected_nodes.items())
            or by_id[129].get('DungeonId') != DUNGEON_ID or by_id[158].get('Count') != 1):
        return
    wake, leave = by_id[135], by_id[133]
    wake_condition = {'Type': 'ReachArea', 'Pos': {'X': -400, 'Y': -270}, 'Range': 5000}
    exit_condition = leave.get('Condition', {})
    if (wake.get('Condition') != wake_condition or leave.get('TidTip') != EXIT_TIP
            or exit_condition.get('Type') != 'DoInteract'
            or [option.get('EntityId') for option in exit_condition.get('AddOptions', [])] != [317750004]):
        return

    occurrences = classify_task_flows(quest, nodes)
    paths = {
        FAINT: ['nodes', 203, 'Actions', 0, 'Params'],
        AWAKENING: ['nodes', 135, 'FinishActions', 1, 'Params'],
        AFTER_EXIT: ['nodes', 12, 'Condition', 'Flow'],
    }
    call_sites = {}
    for key, path in paths.items():
        candidates = occurrences.get(key, [])
        if (len(candidates) != 1 or candidates[0]['path'] != path
                or candidates[0]['context'].get('route_scope') != 'gameplay_node'):
            return
        call_sites[key] = candidates[0]
    if any(_sync_flow(call_sites[key]['caller']) != key for key in (FAINT, AWAKENING)):
        return
    entry_actions = by_id[203].get('Actions', [])
    entrances = [action for action in walk([quest, nodes]) if action.get('Name') == 'TeleportDungeon'
                 and action.get('Params', {}).get('DungeonId') == DUNGEON_ID]
    exits = leave.get('FinishActions', [])
    if (len(entry_actions) <= 5 or entrances != [entry_actions[5]]
            or not synchronous(entrances[0], 'TeleportDungeon')
            or entrances[0]['Params'].get('LocationEntityId') != 317750001
            or len(exits) != 2 or not synchronous(exits[1], 'TeleportDungeon')
            or exits[1].get('Params', {}).get('DungeonId') != 8):
        return

    parsed = _flow_segment(AWAKENING, states, source, choices)
    if (not parsed or parsed['missing_text_ids'] or parsed['unverified_content']
            or [(event['kind'], event.get('text_id')) for event in parsed['events']]
            != [('dialogue', f'Main_HuangLong_SYYLFML_290_{i}') for i in range(1, 8)]):
        return
    before['current_task_continuation'] = {
        **parsed, 'order_scope': 'old_house_dungeon_awakening',
        'scene_title': '【旧屋 · 秧秧醒来】',
        'placement': {
            'after_state': FAINT, 'before_state': AFTER_EXIT,
            'exit_tip': {'entry_index': tip_index, 'text_id': EXIT_TIP},
            'dungeon_id': DUNGEON_ID,
            'flow_call_sites': call_sites,
            'entry_teleport': entrances[0], 'awakening_condition': wake_condition,
            'exit_node_id': leave['Id'], 'exit_condition': exit_condition, 'exit_teleport': exits[1],
            'basis': 'synchronous introduction before dungeon entry, in-dungeon dialogue, and recap exit tip',
            'runtime_verified': False,
        },
    }
    for review in backbone.get('task_only_review', []):
        if review['state_key'] == AWAKENING:
            review.update(classification='placed_in_current_task_reading',
                          reading_anchor_entry_index=before['entry_index'])
