"""Place the documented New Sprout Isle dialogue in its recap stage."""
from ..export_task import flow_key
from ..task_local_order import _flow_segment


QUEST_ID = 145000004
LEVELPLAY_ID = 134000034
ISLE_FLOW = '剧情_1_3_世界_黑海岸_去除污染_16_1'
GREENHOUSE_FLOW = '剧情_1_3_黑海岸主线_5_7'
FACILITY_FLOW = '剧情_1_3_黑海岸主线_6_19'
TIP_NODES = (133, 131, 25, 134)


def add_isle_dialogue(quest, nodes, backbone, states, source, choices, links, audits):
    if quest.get('Id') != QUEST_ID or quest.get('Type') != 1:
        return
    segments = backbone['segments']
    anchors = [s for s in segments if s['state_key'] in (GREENHOUSE_FLOW, FACILITY_FLOW)]
    if ([s['state_key'] for s in anchors] != [GREENHOUSE_FLOW, FACILITY_FLOW]
            or any(s['status'] != 'parsed' for s in anchors)
            or any(s['state_key'] == ISLE_FLOW for s in segments)):
        return
    before, after = anchors
    if 'current_task_continuation' in before or segments[segments.index(before) + 1] is not after:
        return

    eligible = [l for l in links if l['state_key'] == ISLE_FLOW]
    if len(eligible) != 1:
        return
    link = eligible[0]
    if (link['levelplay_id'] != LEVELPLAY_ID or link['node_id'] != 15
            or link['declaration'] != 'l_8_134000034'
            or link['reference_kind'] != 'flow_completion_condition'
            or link['failure_ancestor'] or link['ancestor_types'] != ['Sequence']):
        return
    definitions = [a for a in audits if a['declaration'] == link['declaration']]
    if len(definitions) != 1 or len(definitions[0]['task_conditions']) != 1:
        return
    gate = definitions[0]['task_conditions'][0]
    by_id = {n['Id']: n for n in nodes}
    if (len(by_id) != len(nodes) or not set(TIP_NODES) <= by_id.keys()
            or gate['node_id'] != 131 or gate['source_node']['Condition'] != {
                'Type': 'CheckLevelPlay', 'LevelPlayIds': [LEVELPLAY_ID], 'CompleteNumber': 1}
            or any(by_id[i].get('ParentNodeId') != 19 for i in TIP_NODES[:3])):
        return
    entries = backbone['order_source']['entries']
    tips = [by_id[i].get('TidTip') for i in TIP_NODES]
    tip_positions = [[j for j, e in enumerate(entries) if e.get('TidTip') == tip]
                     for tip in tips]
    start = before['entry_index'] + 1
    if (not all(tips) or tip_positions != [[start + i] for i in range(len(TIP_NODES))]
            or gate['recap_tip_positions'] != tip_positions[1]
            or after['entry_index'] <= tip_positions[-1][0]
            or any(e.get('Flow', {}).get('FlowListName') for e in entries[start:after['entry_index']])):
        return

    reaches_isle = [n for n in definitions[0]['nodes']
                    if n.get('Type') == 'ChildQuest' and n.get('Id') == 7
                    and n.get('Condition') == {'Type': 'CheckConditionGroup', 'Condition': {
                        'Type': 0, 'Conditions': [{'Type': 'CheckChildQuestFinished',
                                                  'QuestId': QUEST_ID, 'ChildQuestId': 133, 'Compare': 'Eq'}]}}]
    if len(reaches_isle) != 1 or flow_key(link['source_condition']['Flow']) != ISLE_FLOW:
        return
    parsed = _flow_segment(ISLE_FLOW, states, source, choices)
    if not parsed or parsed['missing_text_ids'] or len(parsed['events']) < 2:
        return
    prelude, *events = parsed['events']
    if (prelude['kind'] not in {'unparsed_content', 'media_reference'}
            or prelude.get('source_action', {}).get('Name') != 'PlaySequenceData'
            or any(e['kind'] != 'dialogue' for e in events)
            or events[0]['text_id'] != 'Heihaian_main_1_3_2403_1'
            or events[-1]['text_id'] != 'Heihaian_main_1_3_2403_15'):
        return
    before['current_task_continuation'] = {
        **parsed, 'events': events, 'deferred_prelude': prelude,
        'order_scope': 'new_sprout_isle_recap_stage',
        'scene_title': '【新枝地 · 前置演出略】',
        'placement': {
            'after_state': GREENHOUSE_FLOW, 'before_state': FACILITY_FLOW,
            'recap_tips': [{'node_id': i, 'entry_index': p[0], 'text_id': t}
                           for i, p, t in zip(TIP_NODES, tip_positions, tips)],
            'levelplay_flow_call': link, 'arrival_gate': reaches_isle[0]['Condition'],
            'task_completion_gate': gate['source_node']['Condition'],
            'basis': 'owned gameplay flow, exact arrival and completion conditions, and recap stage tips',
            'runtime_sibling_order_verified': False,
        },
    }
