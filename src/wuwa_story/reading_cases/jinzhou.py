"""A reading draft for the chapter's post-battle storytelling scene."""
from hashlib import sha256
import struct

from ..database import vec
from ..sequence_dependencies import entity_config, entity_index
from ..task_local_order import _flow_segment


QUEST_ID = 140800000
FLOW_GROUP = '剧情_新主线_第五章1_10'
STORYTELLER = FLOW_GROUP + '_3'
YUEHUI = FLOW_GROUP + '_1'
ACTIVE = '关卡.Common.状态.激活'
SEATED = '关卡.Common.状态.场景物件交互中'


def _state_change(actions, entity, state):
    expected = {'Type': 'Directly', 'EntityId': entity, 'State': state}
    return next((a for a in actions if a.get('Name') == 'ChangeEntityState'
                 and a.get('Params') == expected and not a.get('Disabled')), None)


def _awake(actions, entity):
    return next((a for a in actions if a.get('Name') == 'AwakeEntity'
                 and entity in a.get('Params', {}).get('EntityIds', [])
                 and not a.get('Disabled')), None)


def build_jinzhou_draft(result, quest, nodes, states, source, choices):
    if quest.get('Id') != QUEST_ID or quest.get('DungeonId') != 8:
        return None
    by_id = {n['Id']: n for n in nodes}
    if not {2, 330, 331} <= by_id.keys() or len(by_id) != len(nodes):
        return None
    seat, finish, setup = (by_id[i] for i in (2, 330, 331))
    if (seat.get('Condition') != {'Type': 'CheckEntityState',
                                  'Conditions': [{'EntityId': 140800590, 'State': SEATED}]}
            or finish.get('Condition') != {'Type': 'CheckEntityState',
                                           'Conditions': [{'EntityId': 140800722, 'State': ACTIVE}]}):
        return None

    chair_awake = _awake(setup.get('Actions', []), 140800590)
    yuehui_awake = _awake(seat.get('EnterActions', []), 140800696)
    exit_awake = _awake(seat.get('FinishActions', []), 140800721)
    scene_activate = _state_change(seat.get('FinishActions', []), 140800592, ACTIVE)
    chapter_ui = next((a for a in finish.get('FinishActions', [])
                       if a.get('Name') == 'PromptQuestChapterUI' and a.get('Params') == {'ChapterState': 1}
                       and not a.get('Disabled')), None)
    if not all((chair_awake, yuehui_awake, exit_awake, scene_activate, chapter_ui)):
        return None

    index = entity_index(source)
    chair = entity_config(index, 8, 140800590)
    exit_trigger = entity_config(index, 8, 140800721)
    if chair is None or exit_trigger is None:
        return None
    seat_actions = [option['Type']['Actions']
                    for option in chair[0].get('InteractComponent', {}).get('Options', [])
                    if option.get('Type', {}).get('Type') == 'Actions']
    if (len(seat_actions) != 1 or not seat_actions[0]
            or seat_actions[0][0].get('Name') != 'LeisureInteract'
            or seat_actions[0][0].get('Params') != {'Option': {'Type': 'SitDown'}}
            or not _state_change(seat_actions[0][1:], 140800590, SEATED)):
        return None
    exit_actions = exit_trigger[0].get('TriggerComponent', {}).get('ExitConfig', {}).get('Actions', [])
    exit_gate = _state_change(exit_actions, 140800722, ACTIVE)
    links = [link for link in result['batch_coverage']['declared_entity_links']
             if (link['map_id'], link['entity_id'], link['component'], link['state_key'])
             == (8, 140800696, 'InteractComponent', YUEHUI)]
    if exit_gate is None or len(links) != 1:
        return None

    groups = [r for r in source.rows('db_flow.db', 'flow') if r['Id'] == FLOW_GROUP]
    if len(groups) != 1:
        return None
    blob = groups[0]['BinData']
    try:
        state_ids = vec(blob, 1)
        if state_ids != vec(blob, 2) or not {1, 3} <= set(state_ids):
            return None
    except (ValueError, struct.error):
        return None
    narration = _flow_segment(STORYTELLER, states, source, choices)
    exchange = _flow_segment(YUEHUI, states, source, choices)
    if (not narration or not exchange or narration['missing_text_ids'] or exchange['missing_text_ids']
            or not any(e.get('text_id') == 'Huanglong_main_1_7_178_1' and e.get('display_name') == '说书人'
                       for e in narration['events'])
            or not any(e.get('text_id') == 'Huanglong_main_1_7_179_2' for e in exchange['events'])):
        return None

    return {
        'basis': 'task_scene_triggers_and_database_dialogue_continuity',
        'runtime_order_verified': False,
        'scene_evidence': {
            'setup_node': 331, 'seat_node': 2, 'chapter_ui_node': 330,
            'chair_awake': chair_awake, 'chair_entity_hash': chair[1], 'chair_actions': seat_actions[0],
            'seat_condition': seat['Condition'], 'scene_activate': scene_activate,
            'exit_awake': exit_awake, 'exit_entity_hash': exit_trigger[1], 'exit_state_change': exit_gate,
            'chapter_ui_condition': finish['Condition'], 'chapter_ui_action': chapter_ui,
            'yuehui_awake': yuehui_awake, 'yuehui_interaction': links[0],
            'flow_group': FLOW_GROUP, 'flow_group_sha256': sha256(blob).hexdigest(),
            'flow_group_state_ids': state_ids, 'narration_direct_trigger_found': False,
            'yuehui_interaction_mandatory_verified': False,
        },
        'entries': [
            {'note': '【战后回到今州。坐下后，场景切入。】'},
            {'segment': narration},
            {'segment': exchange, 'introduction': '【同场可选交谈 · 岳辉】'},
            {'note': '【离开指定区域后，显示章节提示。】'},
        ],
    }
