"""Place the Whispering Town investigation in its documented recap stage."""
from ..dependency_positions import _sync_flow
from ..task_local_order import _flow_segment
from ..terminal_text import synchronous


QUEST_ID = 311000002
LEVELPLAY_ID = 157000002
ARRIVAL = '剧情_2_6_狄斯台地主线_上半_2_1_1'
INVESTIGATION = '剧情_2_6_狄斯台地主线_上半_呓语镇_2_1'
SONORO = '剧情_2_6_狄斯台地主线_上半_2_2_1'


def add_town_investigation(quest, nodes, backbone, states, source, choices, links, audits):
    if quest.get('Id') != QUEST_ID or quest.get('Type') != 1:
        return
    segments = backbone['segments']
    anchors = [s for s in segments if s['state_key'] in (ARRIVAL, SONORO)]
    if ([s['state_key'] for s in anchors] != [ARRIVAL, SONORO]
            or any(s['status'] != 'parsed' for s in anchors)
            or any(s['state_key'] == INVESTIGATION for s in segments)):
        return
    before, after = anchors
    if 'current_task_continuation' in before or segments[segments.index(before) + 1] is not after:
        return

    calls = [link for link in links if link['state_key'] == INVESTIGATION]
    if len(calls) != 1:
        return
    call = calls[0]
    if (call['declaration'] != 'l_8_157000002' or call['levelplay_id'] != LEVELPLAY_ID
            or call['node_id'] != 17 or call['phase'] != 'FinishActions' or call['action_index'] != 0
            or call['failure_ancestor'] or call['ancestor_types'] != ['Sequence', 'Sequence']
            or _sync_flow(call['source_action']) != INVESTIGATION):
        return
    definitions = [audit for audit in audits if audit['declaration'] == call['declaration']]
    if len(definitions) != 1 or len(definitions[0]['task_conditions']) != 1:
        return
    audit = definitions[0]
    task_gate = audit['task_conditions'][0]
    by_id = {n['Id']: n for n in nodes}
    if (len(by_id) != len(nodes) or not {1, 63, 65, 80, 154} <= by_id.keys()
            or task_gate['node_id'] != 63 or task_gate['source_node'] != by_id[63]
            or by_id[80].get('ParentNodeId') != 1
            or any(by_id[i].get('Type') != 'Sequence' for i in (1, 80))
            or any(by_id[i].get('Type') != 'ChildQuest' or by_id[i].get('ParentNodeId') != 80
                   for i in (63, 65, 154))):
        return
    arrival, exploration, enter_sonoro = (by_id[i] for i in (154, 63, 65))
    arrival_condition = arrival.get('Condition', {})
    sonoro_condition = enter_sonoro.get('Condition', {})
    sonoro_calls = [_sync_flow(a) for a in enter_sonoro.get('FinishActions', []) if a.get('Name') == 'PlayFlow']
    if (arrival_condition.get('Type') != 'PlayFlow'
            or _sync_flow({'Name': 'PlayFlow', 'Params': arrival_condition.get('Flow')}) != ARRIVAL
            or exploration.get('Condition') != {
                'Type': 'CheckLevelPlay', 'LevelPlayIds': [LEVELPLAY_ID], 'CompleteNumber': 1}
            or sonoro_condition.get('Type') != 'CheckConditionGroup' or sonoro_calls != [SONORO]):
        return
    switches = {}
    for phase, enabled in (('EnterActions', True), ('FinishActions', False)):
        actions = exploration.get(phase, [])
        if (len(actions) != 1 or not synchronous(actions[0], 'EnableLevelPlay')
                or actions[0].get('Params') != {'Configs': [{'LevelPlayId': LEVELPLAY_ID, 'Enable': enabled}]}):
            return
        switches[phase] = actions[0]

    entries = backbone['order_source']['entries']
    tips = [node.get('TidTip') for node in (exploration, enter_sonoro)]
    tip_positions = [[i for i, entry in enumerate(entries) if tip and entry.get('TidTip') == tip]
                     for tip in tips]
    start = before['entry_index'] + 1
    if (tip_positions != [[start], [start + 1]] or task_gate['recap_tip_positions'] != [start]
            or after['entry_index'] != start + 2
            or any(e.get('Flow', {}).get('FlowListName') for e in entries[start:after['entry_index']])):
        return
    gameplay_nodes = [n for n in audit['nodes'] if n['Id'] == call['node_id']]
    region_condition = {'Type': 'CheckConditionGroup', 'Condition': {'Type': 0, 'Conditions': [
        {'Type': 'CheckInRange', 'RangeEntities': [157750015], 'InRange': True}]}}
    if (len(gameplay_nodes) != 1 or gameplay_nodes[0].get('Type') != 'ChildQuest'
            or gameplay_nodes[0].get('Condition') != region_condition
            or gameplay_nodes[0].get('FinishActions', [])[:1] != [call['source_action']]):
        return

    parsed = _flow_segment(INVESTIGATION, states, source, choices)
    if (not parsed or len(parsed['events']) < 3 or parsed['missing_text_ids'] or parsed['unverified_content']
            or any(event['kind'] != 'dialogue' for event in parsed['events'])
            or parsed['events'][0]['text_id'] != 'Main_Linaxita_2_9_395_2'
            or parsed['events'][-1]['text_id'] != 'Main_Linaxita_2_9_395_25'):
        return
    before['current_task_continuation'] = {
        **parsed, 'order_scope': 'whispering_town_recap_stage',
        'scene_title': '【探索呓语镇】',
        'placement': {
            'after_state': ARRIVAL, 'before_state': SONORO,
            'recap_tips': [{'node_id': node_id, 'entry_index': position[0], 'text_id': tip}
                           for node_id, position, tip in zip((63, 65), tip_positions, tips)],
            'levelplay_flow_call': call, 'region_condition': region_condition,
            'task_completion_gate': exploration['Condition'], 'levelplay_switch_actions': switches,
            'arrival_condition': arrival_condition, 'sonoro_condition': sonoro_condition,
            'basis': 'owned gameplay with synchronous region dialogue between exact recap stage tips',
            'runtime_verified': False,
        },
    }
