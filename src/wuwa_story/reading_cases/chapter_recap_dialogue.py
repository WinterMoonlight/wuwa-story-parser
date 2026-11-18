"""Restore chapter recap dialogue with an exact original-task trigger."""
from ..dependency_positions import _sync_flow
from ..recap_links import linked_levelplays
from ..task_local_order import _flow_segment
from ..terminal_text import synchronous


MAIN = '剧情_1_1_乘宵山主线_'
BATTLE = MAIN + '岁光副本_'
RESTORATIONS = {
    125000121: (MAIN + '2_8', MAIN + '2_13', MAIN + '2_14'),
    125000122: (MAIN + '3_11', MAIN + '3_6', MAIN + '3_4'),
    125000123: (BATTLE + '1_2', BATTLE + '1_4', BATTLE + '1_3'),
}


def _interaction_flow(option):
    kind = option.get('Type', {})
    if option.get('DoIntactType') == 'Direct' and kind.get('Type') == 'Flow':
        return _sync_flow({'Name': 'PlayFlow', 'Params': kind.get('Flow')})
    return None


def _followup(nodes, occurrences, key):
    calls = occurrences.get(key, [])
    node = nodes.get(141, {})
    actions = node.get('FinishActions', [])
    if (len(calls) != 1 or len(actions) <= 1
            or calls[0]['path'] != ['nodes', 141, 'FinishActions', 1, 'Params', 'Option', 'Type', 'Flow']
            or calls[0]['context'].get('route_scope') == 'failure_branch'):
        return None
    unlock = actions[1]
    params = unlock.get('Params', {})
    condition = node.get('Condition', {})
    if (node.get('Type') != 'ChildQuest' or condition.get('Type') != 'PlayFlow'
            or _sync_flow({'Name': 'PlayFlow', 'Params': condition.get('Flow')}) != MAIN + '2_8'
            or not synchronous(unlock, 'AddFlowInteractOption') or params.get('EntityId') != 125900064
            or _interaction_flow(params.get('Option', {})) != key):
        return None
    return {'kind': 'optional_interaction_unlocked_after_flow', 'node_id': 141,
            'completion_condition': condition, 'source_action': unlock,
            'introduction': '【可选交谈 · 继续询问】'}


def _core_interaction(nodes, occurrences, key, entries, index):
    calls = occurrences.get(key, [])
    node = nodes.get(47, {})
    condition = node.get('Condition', {})
    options = condition.get('AddOptions', [])
    if (len(calls) != 1
            or calls[0]['path'] != ['nodes', 47, 'Condition', 'AddOptions', 0, 'Option', 'Type', 'Flow']
            or calls[0]['context'].get('route_scope') == 'failure_branch'
            or node.get('Type') != 'ChildQuest' or condition.get('Type') != 'DoInteract'
            or len(options) != 1 or options[0].get('EntityId') != 125900067
            or _interaction_flow(options[0].get('Option', {})) != key
            or not node.get('TidTip') or entries[index - 1].get('TidTip') != node['TidTip']):
        return None
    return {'kind': 'task_interaction', 'node_id': 47, 'condition': condition, 'tip_entry_index': index - 1}


def _combat_dialogue(nodes, entries, index, source, key):
    enter = nodes.get(78, {})
    end = nodes.get(79, {})
    transfers = [a for a in enter.get('FinishActions', []) if synchronous(a, 'TeleportDungeon')
                 and a.get('Params') == {'DungeonId': 1507, 'IsRegroup': False}]
    gate = end.get('Condition')
    if len(transfers) != 1 or gate != {'Type': 'FinishDungeon', 'Condition': {
            'Type': 'DungeonId', 'DungeonId': 1507, 'Count': 1}}:
        return None
    # Exact recap tips distinguish the story instance from other gameplay on its map.
    gate_tip = end.get('TidTip')
    gate_indices = [i for i, entry in enumerate(entries) if gate_tip and entry.get('TidTip') == gate_tip]
    if len(gate_indices) != 1 or gate_indices[0] >= index:
        return None
    candidates = [a for a in linked_levelplays(list(nodes.values()),
                                              entries[gate_indices[0]:index + 2], source.rows)
                  if not a['definition'].get('RecallConfig')]
    if len(candidates) != 1 or candidates[0]['levelplay_id'] != 141000012:
        return None
    audit = candidates[0]
    if audit['map_id'] != 2041 or audit['dungeon_ids'] != [1507] or key not in audit['flow_references']:
        return None
    battle = [n for n in audit['nodes'] if n['Id'] == 26 and n['Type'] == 'ChildQuest']
    if len(battle) != 1 or battle[0].get('Condition') != {
            'Type': 'DetectCombatState', 'EntityId': 662900000, 'State': '怪物.common.关卡.通信专用.信号3'}:
        return None
    actions = battle[0].get('FinishActions', [])
    if (len(actions) != 1 or actions[0].get('Async') is not True
            or _sync_flow({**actions[0], 'Async': False}) != key):
        return None
    return {'kind': 'dungeon_combat_state', 'dungeon_id': 1507, 'map_id': audit['map_id'],
            'levelplay_id': audit['levelplay_id'], 'node_id': 26, 'condition': battle[0]['Condition'],
            'source_action': actions[0], 'entry_action': transfers[0], 'completion_condition': gate,
            'exact_recap_tips': audit['matched_tip_ids'], 'node_sha256': audit['node_sha256']['141000012_26']}


def restore_dialogue(quest_id, nodes, occurrences, entries, flow_entries, placed, states, source, choices):
    keys = RESTORATIONS.get(quest_id)
    if not keys:
        return {}
    ordered = [(index, key) for key, index in flow_entries.items()]
    matches = [(index, position) for position, (index, key) in enumerate(ordered) if key == keys[1]]
    if len(matches) != 1:
        return {}
    index, position = matches[0]
    if (position == 0 or index in placed
            or tuple(key for _, key in ordered[position - 1:position + 2]) != keys):
        return {}
    by_id = {n['Id']: n for n in nodes}
    if len(by_id) != len(nodes):
        return {}
    key = keys[1]
    if quest_id == 125000121:
        trigger = _followup(by_id, occurrences, key)
    elif quest_id == 125000122:
        trigger = _core_interaction(by_id, occurrences, key, entries, index)
    else:
        trigger = _combat_dialogue(by_id, entries, index, source, key)
    if trigger is None:
        return {}
    segment = _flow_segment(key, states, source, choices)
    if (not segment or not segment['events'] or segment['missing_text_ids'] or segment['unverified_content']
            or any(event['kind'] not in {'dialogue', 'choice'} for event in segment['events'])):
        return {}
    return {index: {**segment, 'trigger': trigger, 'runtime_order_verified': False}}
