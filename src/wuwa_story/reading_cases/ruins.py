"""Place the Floating Ruins battle report in the quest's ascent stage."""
from ..dependency_positions import _sync_flow
from ..task_local_order import _flow_segment
from ..terminal_text import synchronous


QUEST_ID = 102000000
LEVELPLAY_ID = 102800000
PREVIOUS = '剧情_第八章_3_9'
REPORT = '剧情_第八章_10_1'
SUMMIT = '剧情_第八章_6_1'


def add_ruins_battle_report(quest, nodes, backbone, states, source, choices, links, audits):
    if quest.get('Id') != QUEST_ID or quest.get('Type') != 1:
        return
    segments = backbone['segments']
    anchors = [s for s in segments if s['state_key'] in (PREVIOUS, SUMMIT)]
    if ([s['state_key'] for s in anchors] != [PREVIOUS, SUMMIT]
            or any(s['status'] != 'parsed' for s in anchors)
            or any(s['state_key'] == REPORT for s in segments)):
        return
    before, after = anchors
    if 'current_task_continuation' in before or segments[segments.index(before) + 1] is not after:
        return

    calls = [link for link in links if link['state_key'] == REPORT]
    if len(calls) != 1:
        return
    call = calls[0]
    if (call['declaration'] != 'l_8_102800000' or call['levelplay_id'] != LEVELPLAY_ID
            or call['node_id'] != 162 or call['phase'] != 'FinishActions' or call['action_index'] != 0
            or call['failure_ancestor'] or _sync_flow(call['source_action']) != REPORT):
        return
    definitions = [a for a in audits if a['declaration'] == call['declaration']]
    if len(definitions) != 1 or len(definitions[0]['task_conditions']) != 1:
        return
    audit = definitions[0]
    gate = audit['task_conditions'][0]
    gate_node = gate['source_node']
    if (gate['node_id'] != 322 or gate_node['Condition'] != {
            'Type': 'CheckLevelPlay', 'LevelPlayIds': [LEVELPLAY_ID], 'CompleteNumber': 1}):
        return
    switch_actions = []
    for phase, enabled in (('EnterActions', True), ('FinishActions', False)):
        switches = [a for a in gate_node.get(phase, []) if synchronous(a, 'EnableLevelPlay')
                    and a.get('Params') == {'Configs': [{'LevelPlayId': LEVELPLAY_ID, 'Enable': enabled}]}]
        if len(switches) != 1:
            return
        switch_actions.append(switches[0])

    battle_nodes = [n for n in audit['nodes'] if n['Id'] == call['node_id']]
    if len(battle_nodes) != 1:
        return
    battle = battle_nodes[0]
    if (battle['Type'] != 'ChildQuest' or battle.get('Condition', {}).get('Type') != 'Kill'
            or not battle['Condition'].get('TargetsToAwake')
            or battle.get('FinishActions') != [call['source_action']]
            or any(battle.get(k) for k in ('ExitCondition', 'FailedCondition', 'Slots'))):
        return
    tip_nodes = [n for n in nodes if n['Id'] == 331 and n.get('Condition', {}).get('Type') == 'ReachArea']
    if len(tip_nodes) != 1 or not tip_nodes[0].get('TidTip') or not gate_node.get('TidTip'):
        return
    entries = backbone['order_source']['entries']
    tips = [tip_nodes[0]['TidTip'], gate_node['TidTip']]
    positions = [[i for i, entry in enumerate(entries) if entry.get('TidTip') == tip] for tip in tips]
    start = before['entry_index'] + 1
    if (positions != [[start], [start + 1]] or gate['recap_tip_positions'] != [start + 1]
            or after['entry_index'] != start + 2
            or any(e.get('Flow', {}).get('FlowListName') for e in entries[start:after['entry_index']])):
        return

    parsed = _flow_segment(REPORT, states, source, choices)
    if (not parsed or not parsed['events'] or parsed['missing_text_ids'] or parsed['unverified_content']
            or any(e['kind'] != 'dialogue' for e in parsed['events'])
            or parsed['events'][0]['text_id'] != 'Huanglong_main_1_7_65_1'
            or parsed['events'][-1]['text_id'] != 'Huanglong_main_1_7_66_2'):
        return
    before['current_task_continuation'] = {
        **parsed, 'order_scope': 'floating_ruins_ascent_battle',
        'scene_title': '【悬浮废墟 · 击败残象后】',
        'placement': {
            'after_state': PREVIOUS, 'before_state': SUMMIT,
            'recap_tips': [{'entry_index': pos[0], 'text_id': tip} for pos, tip in zip(positions, tips)],
            'levelplay_flow_call': call, 'battle_condition': battle['Condition'],
            'task_node_id': gate['node_id'], 'task_completion_gate': gate_node['Condition'],
            'levelplay_enable_action': switch_actions[0], 'levelplay_disable_action': switch_actions[1],
            'basis': 'owned gameplay with synchronous battle completion dialogue and exact recap stage tips',
            'runtime_verified': False,
        },
    }
