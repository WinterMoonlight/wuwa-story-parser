"""Recover the current Avinoleum battle aftermath beside its legacy recap gap."""
from ..dependency_positions import _sync_flow
from ..task_extras import references
from ..task_local_order import _flow_segment
from ..terminal_text import synchronous


QUEST_ID = 145000005
FAMILY = '剧情_2_2_阿维纽林主线_'
MISSING = FAMILY + '11_27'
RETURN = FAMILY + '12_4'
EPILOGUE_TIP = 'Quest_145000005_ChildQuestTip_145_113'


def _condition_flow(node):
    condition = node.get('Condition', {})
    if node.get('Type') == 'ChildQuest' and set(condition) == {'Type', 'Flow'} and condition['Type'] == 'PlayFlow':
        return _sync_flow({'Name': 'PlayFlow', 'Params': condition['Flow']})
    return None


def add_battle_aftermath(quest, nodes, backbone, states, source, choices=None):
    if quest.get('Id') != QUEST_ID or quest.get('Type') != 1 or MISSING in states or RETURN not in states:
        return
    segments = backbone['segments']
    expected = tuple(FAMILY + suffix for suffix in ('11_25', '11_26', '11_15', '11_27', '16_1'))
    anchors = [s for s in segments if s['state_key'] in expected]
    if (tuple(s['state_key'] for s in anchors) != expected
            or any(s['state_key'] == RETURN for s in segments)):
        return
    first, farewell, movie, gap, epilogue = anchors
    if (any(s['status'] != 'parsed' for s in (first, farewell, movie, epilogue))
            or gap['status'] != 'blocked' or gap.get('error') != 'Missing flow state'
            or 'current_task_continuation' in gap):
        return
    entries = backbone['order_source']['entries']
    tips = [i for i, e in enumerate(entries) if e.get('TidTip') == EPILOGUE_TIP]
    if (movie['entry_index'] + 1 != gap['entry_index']
            or tips != [gap['entry_index'] + 1] or epilogue['entry_index'] != tips[0] + 1):
        return

    by_id = {n['Id']: n for n in nodes}
    if len(by_id) != len(nodes) or not {1, 7, 129, 131, 133, 433, 435, 436} <= by_id.keys():
        return
    battle_stage, epilogue_stage = by_id[131], by_id[7]
    if (by_id[1]['Type'] != 'Sequence' or by_id[1].get('ParentNodeId') != 0
            or any(n['Type'] != 'Sequence' or n.get('ParentNodeId') != 1
                   or any(n.get(k) for k in ('Condition', 'Slots', 'ExitCondition', 'FailedCondition'))
                   for n in (battle_stage, epilogue_stage))):
        return
    battle_nodes = [by_id[i] for i in (129, 433, 435, 436)]
    if ({n['Id'] for n in nodes if n.get('ParentNodeId') == 131} != {129, 433, 435, 436}
            or tuple(map(_condition_flow, battle_nodes)) != (*expected[:3], RETURN)):
        return
    return_node, epilogue_node = battle_nodes[-1], by_id[133]
    if ([n['Id'] for n in nodes if references(n, RETURN)] != [436] or references(quest, RETURN)
            or any(n.get(k) for n in battle_nodes for k in ('Slots', 'ExitCondition', 'FailedCondition'))
            or epilogue_node.get('ParentNodeId') != 7 or epilogue_node.get('TidTip') != EPILOGUE_TIP
            or epilogue_node.get('Condition', {}).get('Type') != 'DoInteract'):
        return
    # The return scene creates an entity that the postlude then removes.
    wake = [a for a in return_node.get('EnterActions', [])
            if synchronous(a, 'AwakeEntity') and a.get('Params') == {'EntityIds': [145750158]}]
    destroy = [a for a in epilogue_node.get('FinishActions', [])
               if synchronous(a, 'DestroyEntity') and 145750158 in a.get('Params', {}).get('EntityIds', [])]
    if len(wake) != 1 or len(destroy) != 1:
        return
    parsed = _flow_segment(RETURN, states, source, choices)
    if (not parsed or parsed['missing_text_ids'] or parsed['unverified_content']
            or not any(e.get('text_id') == 'Main_Linaxita_2_4_140_1' for e in parsed['events'])
            or any(e['kind'] not in {'dialogue', 'choice'} for e in parsed['events'])):
        return
    gap['current_task_continuation'] = {
        **parsed, 'order_scope': 'current_task_battle_aftermath',
        'scene_title': '【战后对白 · 据当前任务配置】',
        'placement': {
            'recap_gap_state': MISSING, 'recap_gap_entry_index': gap['entry_index'],
            'after_movie_state': movie['state_key'], 'before_tip_entry_index': tips[0],
            'battle_stage_id': battle_stage['Id'], 'movie_node_id': 435, 'return_node_id': return_node['Id'],
            'return_condition': return_node['Condition'],
            'epilogue_node_id': epilogue_node['Id'], 'epilogue_condition': epilogue_node['Condition'],
            'entity_wake': wake[0], 'entity_destroy': destroy[0],
            'basis': 'current battle-stage flow and postlude entity lifecycle, anchored by recap movie and tip',
            'legacy_state_equivalence_verified': False, 'runtime_sibling_order_verified': False,
        },
    }
    for review in backbone.get('task_only_review', []):
        if review['state_key'] == RETURN:
            review.update(classification='placed_in_current_task_reading',
                          reading_anchor_entry_index=gap['entry_index'])
