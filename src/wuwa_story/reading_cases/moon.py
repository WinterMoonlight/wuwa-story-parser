"""Reading drafts inferred from the Moon-Chasing task calls and database dialogue."""
from copy import deepcopy
from hashlib import sha256

from ..combined_information import OPTION_FIELDS, jump_target
from ..database import embedded, string
from ..export_task import Exporter, flow_actions, walk
from ..levelplay_order import sync_flow
from ..performance_sources import sequence_source
from ..rendering import render_result
from ..task_flows import classify_task_flows
from ..task_local_order import _flow_segment
from ..terminal_text import synchronous


# Each flow uses a dialogue key from that state to validate the evaluated snapshot.
# Numbers in this manifest are flow references, never sort keys.
FIRST = '剧情_V1.2追月节主线明线_'
SECOND = '剧情_V1.2追月节主线明线（第二周）_'
DARK = '剧情_V1.2追月节主线暗线_'
INVITATION = FIRST + '8_1'
FOLLOWUP_INVITATION = FIRST + '8_2'
SONORO_INSTANCE = 8400
SONORO_LEVELPLAY = 139000001


def _sonoro(flow, text_key=None, **evidence):
    return {'flow': DARK + flow, 'anchor': text_key, 'in_sonoro': True, **evidence}

ORDERS = {
    880000017: (
        {'board': 120101001},
        {'flow': FIRST + '12_1', 'anchor': 'zhuiyuejie_first_13_1'},
        {'flow': FIRST + '23_1', 'anchor': 'zhuiyuejie_first_14_1'},
        {'flow': FIRST + '13_5', 'anchor': 'zhuiyuejie_first_15_1'},
        {'flow': FIRST + '13_1', 'anchor': 'zhuiyuejie_first_16_1'},
        {'flow': FIRST + '13_3', 'anchor': 'zhuiyuejie_first_18_1'},
        {'flow': FIRST + '27_1', 'anchor': 'zhuiyuejie_first_19_1'},
        {'flow': FIRST + '13_4', 'anchor': 'zhuiyuejie_first_20_8'},
        {'flow': FIRST + '15_1', 'anchor': 'zhuiyuejie_first_21_1'},
        {'flow': FIRST + '29_1', 'anchor': 'zhuiyuejie_first_22_24'},
        {'flow': FIRST + '31_1', 'anchor': 'zhuiyuejie_first_23_1'},
    ),
    880000021: (
        {'board': 120101004},
        {'flow': INVITATION, 'anchor': 'zhuiyuejie_first_25_19'},
        {'flow': FOLLOWUP_INVITATION, 'anchor': 'zhuiyuejie_first_26_1', 'if_declined': True},
        {'flow': FIRST + '7_4', 'anchor': 'zhuiyuejie_first_27_1'},
        {'flow': FIRST + '7_3', 'anchor': 'zhuiyuejie_first_28_1'},
        {'flow': FIRST + '7_7', 'anchor': 'zhuiyuejie_first_29_8'},
        {'flow': FIRST + '7_11', 'anchor': 'zhuiyuejie_first_30_1'},
        {'flow': FIRST + '7_12', 'anchor': 'zhuiyuejie_first_31_2'},
        {'flow': FIRST + '7_13', 'anchor': 'zhuiyuejie_first_32_1'},
    ),
    880000025: (
        {'flow': FIRST + '10_10', 'anchor': 'zhuiyuejie_first_33_1'},
        {'board': 120101006},
        {'flow': FIRST + '32_1', 'anchor': 'zhuiyuejie_first_41_1'},
        {'flow': FIRST + '10_2', 'anchor': 'zhuiyuejie_first_35_1'},
        {'flow': FIRST + '10_6', 'anchor': 'zhuiyuejie_first_36_1'},
        {'flow': FIRST + '10_4', 'anchor': 'zhuiyuejie_first_37_1'},
        {'flow': FIRST + '18_1', 'anchor': 'zhuiyuejie_first_38_1'},
    ),
    880000032: (
        {'flow': SECOND + '4_1', 'anchor': 'zhuiyuejie_second_1_2'},
        {'flow': SECOND + '4_3', 'anchor': 'zhuiyuejie_second_3_9'},
        {'flow': SECOND + '4_4', 'anchor': 'zhuiyuejie_second_4_1'},
        {'flow': SECOND + '1_1', 'anchor': 'zhuiyuejie_second_5_22'},
        {'flow': DARK + '4_1', 'anchor': 'zhuiyuejie_second_6_4'},
        {'flow': DARK + '4_2', 'anchor': 'zhuiyuejie_second_6_7'},
        {'flow': DARK + '4_3', 'anchor': 'zhuiyuejie_second_6_10'},
        _sonoro('1_1', 'zhuiyuejie_second_7_1'),
        _sonoro('1_6', 'zhuiyuejie_second_12_1'),
        _sonoro('1_36', 'zhuiyuejie_second_13_1'),
        _sonoro('1_37', 'zhuiyuejie_second_14_1'),
        _sonoro('1_38', 'zhuiyuejie_second_15_4'),
        {'gap': '【调查桌上的心愿纸，部分操作与对白暂略】', 'fill': (
            _sonoro('1_51', 'Flow_139700000_1310', node=97, action_index=0,
                    papers=(120101015, 120101016, 120101017)),
            _sonoro('1_47', 'zhuiyuejie_second_19_1', node=97, action_index=1,
                    papers=(120101018, 120101019)),
            _sonoro('1_48', 'zhuiyuejie_second_22_1', node=78),
        )},
        _sonoro('1_9', 'zhuiyuejie_second_23_3'),
        _sonoro('1_39', 'zhuiyuejie_second_24_1'),
        _sonoro('1_40', 'zhuiyuejie_second_25_12'),
        _sonoro('1_41', 'zhuiyuejie_second_27_1'),
        _sonoro('1_11', 'zhuiyuejie_second_26_1'),
        _sonoro('1_12', 'zhuiyuejie_second_31_1'),
        _sonoro('1_44', 'zhuiyuejie_second_36_1'),
        _sonoro('1_42', 'zhuiyuejie_second_35_1'),
        _sonoro('1_45', 'zhuiyuejie_second_39_1'),
        {'gap': '【途中几段虚影交互暂略】', 'fill': (
            _sonoro('1_23', 'zhuiyuejie_second_40_1', node=162, wake=(161, 139700067)),
            _sonoro('1_22', 'zhuiyuejie_second_41_1', node=164, wake=(163, 139700068)),
            _sonoro('1_24', 'zhuiyuejie_second_42_1', node=166, wake=(165, 139700073)),
            _sonoro('1_25', 'zhuiyuejie_second_43_1', node=168, wake=(167, 139700105)),
            _sonoro('1_26', 'zhuiyuejie_second_45_1', node=170, wake=(169, 139700071)),
        )},
        _sonoro('1_28', 'zhuiyuejie_second_46_1'),
        _sonoro('1_29', 'zhuiyuejie_second_47_1'),
        {'gap': '【战斗过程及部分对白暂略】', 'fill': (
            _sonoro('1_30', 'zhuiyuejie_second_48_1', node=126, battle_tag=(700004, '1.2Boss首次倒地', 0)),
            _sonoro('2_1', node=95, battle_tag=(700002, '1.2Boss弹出对话', 0), asset='DA_R0012'),
            _sonoro('1_32', 'zhuiyuejie_second_50_1', node=128, gender_nodes=(128, 130)),
            _sonoro('1_31', 'zhuiyuejie_second_49_1', node=123, battle_tag=(700003, '1.2Boss处决演出', 0)),
            _sonoro('2_2', node=123, battle_tag=(700003, '1.2Boss处决演出', 2), asset='DA_R0014'),
        )},
        _sonoro('1_35', 'zhuiyuejie_second_51_47'),
        _sonoro('1_50', 'zhuiyuejie_second_60_1'),
        _sonoro('3_1', 'Flow_139700000_709'),
        {'flow': SECOND + '4_5', 'anchor': 'zhuiyuejie_second_52_1'},
        {'flow': SECOND + '4_6', 'anchor': 'zhuiyuejie_second_53_19'},
        {'flow': SECOND + '2_1', 'anchor': 'zhuiyuejie_second_58_2'},
    ),
}


def _existing_flows(result):
    matches = {}
    for group_index, group in enumerate(result['task_local_sequences']):
        for segment_index, segment in enumerate(group['segments']):
            key = segment['state_key']
            matches[key] = None if key in matches else (segment, [group_index, segment_index])
    return matches


def _board_pointer(result, board_id):
    matches = [(index, entry) for index, entry in enumerate(result.get('external_content', []))
               if entry.get('information_board', {}).get('board_id') == board_id]
    if len(matches) != 1:
        return None
    index, entry = matches[0]
    if len(entry.get('texts', [])) != 2 or any(not text.get('raw_text') for text in entry['texts']):
        return None
    return index


def _sonoro_source(nodes, source):
    enters = [node['Id'] for node in nodes for value in walk(node)
              if value.get('Name') == 'TeleportDungeon'
              and value.get('Params', {}).get('DungeonId') == SONORO_INSTANCE]
    exits = [node['Id'] for node in nodes
             if node.get('Condition', {}).get('Type') == 'FinishDungeon'
             and node['Condition'].get('Condition', {}).get('DungeonId') == SONORO_INSTANCE]
    if len(enters) != 1 or len(exits) != 1:
        return None, {}, {}
    instances = [r for r in source.rows('db_instance_dungeon.db', 'instancedungeon')
                 if r['Id'] == SONORO_INSTANCE and r['MapConfigId'] == SONORO_INSTANCE]
    levels = [r for r in source.rows('db_LevelPlayData.db', 'levelplaydata')
              if r['LevelPlayId'] == SONORO_LEVELPLAY]
    if len(instances) != 1 or len(levels) != 1:
        return None, {}, {}
    configs = [v for _, v in embedded(levels[0]['BinData']) if isinstance(v, dict)]
    if (len(configs) != 1 or configs[0].get('Type') != 'Dungeon'
            or configs[0].get('LevelId') != SONORO_INSTANCE or configs[0].get('RecallConfig')):
        return None, {}, {}
    level_rows = [r for r in source.rows('db_LevelPlayNodeData.db', 'levelplaynodedata')
                  if r['Key'].startswith(f'{SONORO_LEVELPLAY}_')]
    level_nodes = [embedded(r['BinData'])[0][1] for r in level_rows]
    return {
        'instance_id': SONORO_INSTANCE, 'levelplay_id': SONORO_LEVELPLAY,
        'enter_task_node': enters[0], 'completion_task_node': exits[0],
        'levelplay_sha256': sha256(levels[0]['BinData']).hexdigest(),
    }, classify_task_flows(configs[0], level_nodes), {n['Id']: n for n in level_nodes}


def _invitation_confirmed(segment):
    return any(write['variable'].get('Name') == '确认前往找奶奶' and write['recorded_constant'] is True
               for audit in segment['unverified_content'] if audit['kind'] == 'isolated_constant_write_audit'
               for write in audit['trace'])


def _wish_paper_menu(parser, actions, boards):
    """Project only the two linear menus whose prerequisites are earlier reads."""
    if [a['Name'] for a in actions] not in (['SetPlotMode', 'ShowTalk'],
                                           ['SetPlotMode', 'ShowTalk', 'DestroyEntity']):
        raise ValueError('Unexpected wish-paper flow')
    show = actions[1]
    items = show['Params']['TalkItems']
    menu = items[-1]
    if (not synchronous(show, 'ShowTalk') or set(show['Params']) != {'TalkItems'}
            or any(item.get('Type') != 'Talk' or item.get('Actions') or item.get('Options')
                   for item in items[:-1])
            or menu.get('Type') != 'Option' or set(menu) != {'Type', 'Id', 'Name', 'Options'}
            or len(menu['Options']) != len(boards)):
        raise ValueError('Unexpected wish-paper menu')
    for index, (option, board_id) in enumerate(zip(menu['Options'], boards)):
        condition = {'Type': 'PreOption', 'PreOptions': list(range(index))} if index else None
        panel, continuation = option['Actions']
        if (set(option) - OPTION_FIELDS - {'ReadMarkEnabled', 'PreCondition'}
                or option.get('PreCondition') != condition or option.get('ReadMarkEnabled') is not True
                or not synchronous(panel, 'OpenSystemBoard')
                or panel['Params'] != {'SystemType': 'InformationView', 'BoardId': board_id}):
            raise ValueError('Unexpected wish-paper option')
        if index < len(boards) - 1:
            if jump_target([continuation]) != menu['Id']:
                raise ValueError('Wish-paper menu does not reopen')
        elif not synchronous(continuation, 'FinishTalk') or continuation['Params'] != {}:
            raise ValueError('Wish-paper menu does not finish')
    # Only the next unread option can advance the route. The existing loop
    # reader visits options in that order after the proven guards are removed.
    choice_key = f'{parser.state_key}:{menu["Id"]}'
    if parser.choices.get(choice_key, 0) != 0:
        raise ValueError('The first paper must be read before the others')
    projected = deepcopy(actions)
    for option in projected[1]['Params']['TalkItems'][-1]['Options']:
        option.pop('PreCondition', None)
    if parser.actions(projected):
        raise ValueError('Unexpected wish-paper control')
    resolved_boards = [e['information_board']['board_id'] for e in parser.events
                       if e['kind'] == 'information_board']
    if ([v['selected_index'] for v in parser.decisions] != list(range(len(boards)))
            or resolved_boards != list(boards)
            or any(e['kind'] == 'unparsed_content' for e in parser.events)):
        raise ValueError('Wish-paper text was not fully recovered')
    for decision in parser.decisions:
        for rendered, original in zip(decision['options'], menu['Options']):
            if 'PreCondition' in original:
                rendered['source_condition'] = original['PreCondition']
    parser.unverified_content.append({'kind': 'wish_paper_prerequisite_order', 'talk_id': menu['Id'],
                                      'board_ids': list(boards), 'runtime_verified': False})


def _sonoro_special_segment(step, states, source, choices):
    key = step['flow']
    try:
        blob = states[key]['BinData']
        actions, fields = flow_actions(blob)
        parser = Exporter(source=source, choices=choices, allow_incomplete=True, configured_text_order=True)
        parser.state_key = key
        if 'papers' in step:
            _wish_paper_menu(parser, actions, step['papers'])
        else:
            show = actions[-1]
            params = show['Params']
            path = params['SequenceDataAsset']
            asset = step['asset']
            empty = {'TalkItems': [], 'TalkSequence': [], 'SequenceNames': [], 'SequenceTransitions': {}}
            if (not synchronous(show, 'ShowTalk') or not path.endswith(f'/{asset}.{asset}')
                    or [a['Name'] for a in actions[:-1]] != ['SetPlotMode', 'HideByRangeInFlow']
                    or params != {'SequenceDataAsset': path, **empty}):
                return None
            evidence = sequence_source(path, source.rows)
            parser.events.append({'kind': 'media_reference', 'state_key': key, 'source_action': show,
                                  'source_resolution': evidence, 'media': evidence.get('media', {}),
                                  'raw_text': '【战斗演出内容待核验】'})
        if parser.missing:
            return None
    except (ValueError, KeyError, TypeError, IndexError):
        return None
    rendered = render_result({'title': '', 'events': parser.events, 'route': {'choices': parser.decisions}})
    return {'state_key': key, 'events': rendered['events'], 'route': rendered['route'],
            'source_actions': actions, 'action_fields': fields, 'sha256': sha256(blob).hexdigest(),
            'unverified_content': parser.unverified_content, 'missing_text_ids': []}


def _checked_sonoro_sites(step, sites, dungeon_nodes, source):
    if 'gender_nodes' in step:
        expected = {step['gender_nodes'][0]: '女', step['gender_nodes'][1]: '男'}
        if (len(sites) != len(expected) or {s['path'][1] for s in sites} != expected.keys() or any(
                site['path'][2:] != ['FinishActions', 2, 'Params']
                or site['context']['ancestry'][0]['Condition'] != {
                    'Type': 'CheckConditionGroup', 'Condition': {'Type': 0, 'Conditions': [
                        {'Type': 'CheckPlayerGender', 'Gender': expected[site['path'][1]]}]}}
                for site in sites)):
            return None
    elif len(sites) != 1:
        return None
    site = next((s for s in sites if s['path'][1] == step['node']), None)
    if site is None:
        return None
    if 'action_index' in step:
        option_path = ['Condition', 'AddOptions', 0, 'Option', 'Type', 'Actions']
        if site['path'][2:] != [*option_path, step['action_index'], 'Params'] or not sync_flow(site['caller']):
            return None
    evidence = {'call_site': site}
    if 'wake' in step:
        wake_id, entity = step['wake']
        wake_node = dungeon_nodes.get(wake_id, {})
        interaction = dungeon_nodes[step['node']]
        condition = interaction['Condition']
        if (site['path'][2:] != ['Condition', 'AddOptions', 0, 'Option', 'Type', 'Flow']
                or condition.get('Type') != 'DoInteract' or len(condition.get('AddOptions', [])) != 1
                or condition['AddOptions'][0]['EntityId'] != entity
                or wake_node.get('ParentNodeId') != interaction.get('ParentNodeId')
                or wake_node.get('Condition', {}).get('Type') != 'ReachArea'):
            return None
        wakes = [action for action in wake_node.get('FinishActions', [])
                 if synchronous(action, 'AwakeEntity') and action['Params'] == {'EntityIds': [entity]}]
        if len(wakes) != 1:
            return None
        evidence['entity_wake'] = {'node_id': wake_id, 'source_action': wakes[0]}
    if 'battle_tag' in step:
        tag, description, finish_index = step['battle_tag']
        condition = site['context']['ancestry'][0].get('Condition', {})
        if (site['path'][2:] != ['FinishActions', finish_index, 'Params']
                or condition != {'Type': 'WaitBattleCondition', 'Count': 0, 'Option': [
                    {'Type': 'BattleTag', 'EntityId': 139700099, 'TagConfigId': tag}]}):
            return None
        matches = [row for row in source.rows('db_battletag.db', 'battletag') if row['Id'] == tag]
        if len(matches) != 1 or string(matches[0]['BinData'], 1) != description:
            return None
        evidence['battle_tag_source'] = {'id': tag, 'description': description,
                                         'table': 'db_battletag.db/battletag',
                                         'sha256': sha256(matches[0]['BinData']).hexdigest()}
    if len(sites) > 1:
        evidence['equivalent_call_sites'] = [s for s in sites if s is not site]
    return evidence


def build_moon_draft(result, quest, nodes, states, source, choices):
    steps = ORDERS.get(quest['Id'])
    if not steps or quest.get('Type') != 1:
        return None
    calls = classify_task_flows(quest, nodes)
    dungeon, dungeon_calls, dungeon_nodes = (
        _sonoro_source(nodes, source) if any(s.get('in_sonoro') for s in steps) else (None, {}, {}))
    existing = _existing_flows(result)
    entries, selected = [], set()
    invitation_confirmed = False

    def resolve(step):
        entry = {k: v for k, v in step.items() if k not in
                 {'node', 'action_index', 'papers', 'battle_tag', 'asset', 'gender_nodes', 'wake'}}
        if 'board' in step:
            index = _board_pointer(result, step['board'])
            if index is None:
                return None
            entry['external_index'] = index
        if 'flow' in step:
            key = step['flow']
            sites = (dungeon_calls if step.get('in_sonoro') else calls).get(key, [])
            if any(site['kind'] == 'failure_branch' for site in sites) or key in selected:
                return None
            if 'node' in step:
                evidence = _checked_sonoro_sites(step, sites, dungeon_nodes, source)
                if evidence is None:
                    return None
            elif len(sites) == 1:
                evidence = {'call_site': sites[0]}
            else:
                return None
            if key in existing:
                if existing[key] is None:
                    return None
                segment, entry['local_segment'] = existing[key]
            else:
                segment = (_sonoro_special_segment(step, states, source, choices)
                           if 'papers' in step or 'asset' in step else
                           _flow_segment(key, states, source, choices, record_constant_writes=True))
                if segment is None:
                    return None
                entry['segment'] = segment
            if step['anchor'] and not any(e.get('text_id') == step['anchor'] for e in segment['events']):
                return None
            entry.update(evidence)
        return entry

    for step in steps:
        if step.get('if_declined') and invitation_confirmed:
            continue
        if 'fill' in step:
            replacements = [resolve(candidate) for candidate in step['fill']]
            if all(replacements):
                entries.extend(replacements)
                selected.update(entry['flow'] for entry in replacements)
            else:
                entries.append({'gap': step['gap']})
            continue
        entry = resolve(step)
        if entry is None:
            return None
        if 'flow' in entry:
            key = entry['flow']
            selected.add(key)
            if key in {INVITATION, FOLLOWUP_INVITATION}:
                segment = existing[key][0] if 'local_segment' in entry else entry['segment']
                invitation_confirmed = _invitation_confirmed(segment)
        entries.append(entry)
        if step.get('if_declined') and not invitation_confirmed:
            entries.append({'gap': '【尚未答应出发，后续剧情暂略】'})
            break
    return {
        'basis': 'database_dialogue_continuity_and_task_calls',
        'runtime_order_verified': False,
        'entries': entries,
        'other_task_references': sorted(set(calls) - selected),
        'dungeon': dungeon,
        'other_dungeon_references': sorted(set(dungeon_calls) - selected),
    }
