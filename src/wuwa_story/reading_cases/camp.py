"""Place the optional camp conversation within its recap stage."""
from ..dependency_positions import _sync_flow
from ..entity_trigger_timing import _lifecycle_actions
from ..task_flows import classify_task_flows
from ..task_local_order import _flow_segment
from ..terminal_text import synchronous


QUEST_ID = 140000004
ENTITY_ID = 140800001
FAMILY = '剧情_新主线_第五章1_1_'
ARRIVAL = FAMILY + '2'
CAMP_TALK = FAMILY + '11'
MESSENGER = FAMILY + '16'
CAMP_TIP = 'Quest_140000004_ChildQuestTip_140_95'


def add_camp_conversation(quest, nodes, backbone, states, source, choices, links):
    if quest.get('Id') != QUEST_ID or quest.get('Type') != 1:
        return
    segments = backbone['segments']
    anchors = [s for s in segments if s['state_key'] in (ARRIVAL, MESSENGER)]
    if ([s['state_key'] for s in anchors] != [ARRIVAL, MESSENGER]
            or any(s['status'] != 'parsed' for s in anchors)
            or any(s['state_key'] == CAMP_TALK for s in segments)):
        return
    arrival, messenger = anchors
    if 'current_task_continuation' in arrival or segments[segments.index(arrival) + 1] is not messenger:
        return
    entries = backbone['order_source']['entries']
    tip_index = arrival['entry_index'] + 1
    if ([i for i, entry in enumerate(entries) if entry.get('TidTip') == CAMP_TIP] != [tip_index]
            or messenger['entry_index'] != tip_index + 1):
        return

    matches = [link for link in links if link['state_key'] == CAMP_TALK or link['entity_id'] == ENTITY_ID]
    if len(matches) != 1:
        return
    link = matches[0]
    if (link['state_key'] != CAMP_TALK or link['map_id'] != 8 or link['entity_id'] != ENTITY_ID
            or link['component'] != 'InteractComponent'):
        return
    component = link['source_component']
    options = component.get('Options', [])
    if component.get('Disabled') or len(options) != 1:
        return
    interaction = options[0].get('Type', {})
    if interaction.get('Type') != 'Flow' or _sync_flow({'Name': 'PlayFlow', 'Params': interaction.get('Flow')}) != CAMP_TALK:
        return

    by_id = {node['Id']: node for node in nodes}
    if len(by_id) != len(nodes) or not {30, 31, 110, 334} <= by_id.keys():
        return
    wake, investigate, destroy = (by_id[i] for i in (30, 31, 110))
    if (by_id[334].get('Type') != 'Sequence'
            or any(n.get('Type') != 'ChildQuest' or n.get('ParentNodeId') != 334
                   for n in (wake, investigate, destroy))
            or investigate.get('TidTip') != CAMP_TIP or investigate.get('Condition', {}).get('Type') != 'ReachArea'):
        return
    occurrences = classify_task_flows(quest, nodes)
    arrival_calls, messenger_calls = (occurrences.get(key, []) for key in (ARRIVAL, MESSENGER))
    if (occurrences.get(CAMP_TALK) or len(arrival_calls) != 1 or len(messenger_calls) != 1
            or arrival_calls[0]['path'] != ['nodes', 30, 'FinishActions', 4, 'Params']
            or messenger_calls[0]['path'] != ['nodes', 110, 'Condition', 'Flow']
            or any(call['context'].get('route_scope') != 'gameplay_node'
                   for call in (arrival_calls[0], messenger_calls[0]))
            or _sync_flow(arrival_calls[0]['caller']) != ARRIVAL
            or destroy.get('Condition', {}).get('Type') != 'PlayFlow'):
        return
    lifecycle = {(n['Id'], *path): action for n in nodes
                 for path, action, ids in _lifecycle_actions(n) if ENTITY_ID in ids}
    wake_path = (30, 'FinishActions', 2)
    destroy_path = (110, 'EnterActions', 1)
    if (lifecycle.keys() != {wake_path, destroy_path}
            or not synchronous(lifecycle[wake_path], 'AwakeEntity')
            or not synchronous(lifecycle[destroy_path], 'DestroyEntity')):
        return

    parsed = _flow_segment(CAMP_TALK, states, source, choices)
    if (not parsed or parsed['missing_text_ids'] or parsed['unverified_content']
            or [(event['kind'], event.get('text_id')) for event in parsed['events']]
            != [('dialogue', f'Huanglong_main_1_7_5_{i}') for i in (1, 7, 8, 2, 3, 4, 5, 6)]):
        return
    arrival['current_task_continuation'] = {
        **parsed, 'order_scope': 'camp_entity_interaction_recap_stage',
        'scene_title': '【检查营地 · 可选交谈】',
        'optional': True,
        'placement': {
            'after_state': ARRIVAL, 'before_state': MESSENGER,
            'recap_tip': {'node_id': 31, 'entry_index': tip_index, 'text_id': CAMP_TIP},
            'entity_interaction': link,
            'awake': {'source_path': list(wake_path), 'source_action': lifecycle[wake_path]},
            'destroy': {'source_path': list(destroy_path), 'source_action': lifecycle[destroy_path]},
            'arrival_call': arrival_calls[0], 'messenger_condition': destroy['Condition'],
            'basis': 'entity interaction during the documented camp inspection stage',
            'runtime_verified': False,
        },
    }
