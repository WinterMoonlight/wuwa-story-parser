"""Read the library's completion dialogue before the Scar encounter."""
from ..dependency_positions import _sync_flow
from ..recap_links import linked_levelplays
from ..task_local_order import _flow_segment
from ..terminal_text import synchronous


QUEST_ID = 139000031
LIBRARY_FLOW = '剧情_主线_龙主居所临时占位剧情_6_2'
CONFRONTATION = '剧情_新主线_CE版_第一章_第五幕_庭际刀刃鸣_3_4'
BOSS_INTRO = '剧情_伤痕演出_3_1'


def add_library_confrontation(quest, nodes, backbone, states, source, choices=None):
    if quest.get('Id') != QUEST_ID or quest.get('Type') != 1 or CONFRONTATION not in states:
        return
    segments = backbone['segments']
    anchors = [s for s in segments if s['state_key'] in (LIBRARY_FLOW, BOSS_INTRO)]
    if ([s['state_key'] for s in anchors] != [LIBRARY_FLOW, BOSS_INTRO]
            or any(s['status'] != 'parsed' for s in anchors)
            or any(s['state_key'] == CONFRONTATION for s in segments)):
        return
    library, boss = anchors
    if 'current_task_continuation' in library or segments[segments.index(library) + 1] is not boss:
        return
    entries = backbone['order_source']['entries']
    task_by_id = {n['Id']: n for n in nodes}
    if len(task_by_id) != len(nodes) or not {86, 96, 104} <= task_by_id.keys():
        return
    library_gate, boss_gate, entrance = (task_by_id[i] for i in (86, 96, 104))
    if (library_gate.get('Condition') != {'Type': 'FinishDungeon', 'Condition': {
            'Type': 'DungeonId', 'DungeonId': 49, 'Count': 1, 'IsExitDungeon': True}}
            or boss_gate.get('Condition') != {'Type': 'FinishDungeon', 'Condition': {
                'Type': 'DungeonId', 'DungeonId': 1503, 'Count': 1}}
            or entrance.get('Condition') != {'Type': 'EnterDungeon',
                'EnterType': {'Type': 'DungeonId', 'DungeonId': 49}}):
        return
    found = linked_levelplays(nodes, entries, source.rows)
    if sorted(link['levelplay_id'] for link in found) != [123000037, 131000071]:
        return
    library_play, boss_play = sorted(found, key=lambda link: link['levelplay_id'])
    if (49 not in library_play['dungeon_ids'] or 1503 not in boss_play['dungeon_ids']
            or LIBRARY_FLOW not in library_play['flow_references']
            or BOSS_INTRO not in boss_play['flow_references']
            or CONFRONTATION in boss_play['flow_references']):
        return

    library_nodes = {n['Id']: n for n in library_play['nodes']}
    completions = [n for n in library_play['nodes'] if n['Type'] == 'QuestSucceed']
    if len(library_nodes) != len(library_play['nodes']) or len(completions) != 1 or 81 not in library_nodes:
        return
    investigation, success = library_nodes[81], completions[0]
    expected_tips = [boss_gate.get('TidTip'), 'LevelPlay_131000071_ChildQuestTip_0_6']
    if (investigation.get('TidTip') != entries[library['entry_index'] - 1].get('TidTip')
            or investigation.get('TidTip') not in library_play['matched_tip_ids']
            or expected_tips[-1] not in boss_play['matched_tip_ids']
            or [e.get('TidTip') for e in entries[library['entry_index'] + 1:boss['entry_index']]] != expected_tips):
        return
    complete = investigation.get('FinishActions', [])
    transition = success.get('FinishActions', [])
    if (len(complete) != 2 or _sync_flow(complete[0]) != LIBRARY_FLOW
            or not synchronous(complete[1], 'FinishDungeon') or complete[1]['Params'] != {'IsSuccess': True}
            or len(transition) != 2 or _sync_flow(transition[0]) != CONFRONTATION
            or not synchronous(transition[1], 'TeleportDungeon')
            or transition[1]['Params'] != {'DungeonId': 1503, 'IsRegroup': False}):
        return
    parsed = _flow_segment(CONFRONTATION, states, source, choices)
    if (not parsed or not parsed['events'] or parsed['missing_text_ids'] or parsed['unverified_content']
            or any(e['kind'] != 'dialogue' for e in parsed['events'])
            or parsed['events'][0]['text_id'] != 'Huanglong_main_1_5_76_1'
            or parsed['events'][-1]['text_id'] != 'Huanglong_main_1_5_76_9'):
        return
    library['current_task_continuation'] = {
        **parsed, 'order_scope': 'library_success_before_boss_dungeon',
        'scene_title': '【瑝览类书 · 伤痕现身】',
        'placement': {
            'after_state': LIBRARY_FLOW, 'before_state': BOSS_INTRO,
            'library_levelplay_id': library_play['levelplay_id'], 'boss_levelplay_id': boss_play['levelplay_id'],
            'task_entrance_condition': entrance['Condition'],
            'task_completion_conditions': [library_gate['Condition'], boss_gate['Condition']],
            'investigation_node': investigation, 'success_node': success,
            'node_sha256': {f'123000037_{n["Id"]}': library_play['node_sha256'][f'123000037_{n["Id"]}']
                            for n in (investigation, success)},
            'basis': 'successful library completion followed by synchronous dialogue and boss dungeon transfer',
            'runtime_verified': False,
        },
    }
