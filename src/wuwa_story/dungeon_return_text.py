"""Read local completion dialogue and success transitions without ordering siblings."""
from copy import deepcopy

from .database import rows
from .export_task import Exporter, flow_actions, flow_key
from .rendering import render_result


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _flow(value):
    if not isinstance(value, dict) or set(value) != {'FlowListName', 'FlowId', 'StateId'}:
        return None
    if not isinstance(value['FlowListName'], str) or not value['FlowListName']:
        return None
    if any(type(value[key]) is not int or value[key] <= 0 for key in ('FlowId', 'StateId')):
        return None
    return flow_key(value)


def _sync(action):
    return (isinstance(action, dict)
            and not set(action) - {'Name', 'Params', 'Async', 'ActionGuid', 'ActionId'}
            and action.get('Async', False) is False)


def _read(key, source):
    read_rows = source.rows if source is not None else rows
    matches = [row for row in read_rows('db_flowState.db', 'flowstate') if row['StateKey'] == key]
    if len(matches) != 1:
        return None
    try:
        actions, fields = flow_actions(matches[0]['BinData'])
        parser = Exporter(allow_incomplete=True, source=source)
        parser.state_key = key
        if (parser.actions(actions) or parser.missing or parser.unverified_content
                or parser.decisions or parser.unordered_attachments):
            return None
        result = render_result({'title': '', 'route': {'choices': parser.decisions}, 'events': parser.events})
        if not result['events']:
            return None
        return {'state_key': key, 'events': result['events'], 'route': result['route'],
                'source_actions': actions, 'equivalent_action_fields': fields}
    except (ValueError, KeyError, TypeError, IndexError):
        return None


def dungeon_return_sections(result, task_nodes, audits, source):
    entries = result.get('source', {}).get('order_source', {}).get('entries', [])
    if not entries:
        entries = (result.get('recap_backbone') or {}).get('order_source', {}).get('entries', [])
    sections = []
    for audit in audits:
        link = audit.get('dungeon_link')
        if not link:
            continue
        dungeon_id = link['dungeon_id']
        targets = [node for node in task_nodes if node.get('Condition') == {
            'Type': 'FinishDungeon', 'Condition': {'Type': 'DungeonId', 'DungeonId': dungeon_id, 'Count': 1}}]
        if len(targets) != 1:
            continue
        target = targets[0]
        entry_calls = [action for action in target.get('EnterActions', [])
                       if action.get('Name') == 'TeleportDungeon']
        if (len(entry_calls) != 1 or not _sync(entry_calls[0])
                or entry_calls[0].get('Params', {}).get('DungeonId') != dungeon_id):
            continue
        tips = [(index, entry) for index, entry in enumerate(entries)
                if target.get('TidTip') and entry.get('TidTip') == target['TidTip']]
        if (len(tips) != 1 or tips[0][1].get('Flow') != {'FlowListName': '', 'FlowId': 0, 'StateId': 0}):
            continue
        nodes = audit['nodes']
        finishes = [(node, index, action) for node in nodes
                    for index, action in enumerate(node.get('FinishActions', []))
                    if action.get('Name') == 'FinishDungeon']
        if len(finishes) != 1 or finishes[0][2].get('Params') != {'IsSuccess': True} or not _sync(finishes[0][2]):
            continue
        finish_node, finish_index, finish_action = finishes[0]
        all_finishes = [value for value in _walk(nodes) if value.get('Name') == 'FinishDungeon']
        if len(all_finishes) != 1 or all_finishes[0] != finish_action:
            continue
        actions = finish_node['FinishActions']
        # Only a direct synchronous dialogue followed by known control reset.
        if finish_index >= 2:
            call, reset = actions[finish_index - 2:finish_index]
            key = _flow(call.get('Params')) if _sync(call) and call.get('Name') == 'PlayFlow' else None
            if key and _sync(reset) and reset.get('Name') == 'SetPlayerOperationRestriction' and reset.get('Params') == {'Type': 'EnableAll'}:
                text = _read(key, source)
                if text:
                    sections.append({**text, 'scope': 'before_explicit_dungeon_completion',
                        'dungeon_id': dungeon_id, 'levelplay_id': audit['levelplay_id'],
                        'entry_index': tips[0][0], 'task_node_id': target['Id'],
                        'source_node': deepcopy(finish_node), 'dungeon_link': link,
                        'proof': {'source_actions': actions[finish_index - 2:finish_index + 1],
                                  'relative_section_order_verified': False, 'runtime_verified': False}})
        successes = [node for node in nodes if node.get('Type') == 'QuestSucceed']
        if len(successes) != 1:
            continue
        success = successes[0]
        for action in success.get('FinishActions', []):
            params = action.get('Params', {})
            transition = params.get('TransitionOption', {}) if isinstance(params, dict) else {}
            if (not _sync(action) or action.get('Name') != 'TeleportDungeon'
                    or not isinstance(params, dict)
                    or set(params) - {'DungeonId', 'IsRegroup', 'TransitionOption', 'LocationEntityId'}
                    or params.get('IsRegroup', False) is not False
                    or set(transition) != {'Type', 'CenterTextFlow'} or transition['Type'] != 'CenterText'):
                continue
            destination_id = params.get('DungeonId')
            if type(destination_id) is not int or destination_id <= 0:
                continue
            read_rows = source.rows if source is not None else rows
            destinations = [row for row in read_rows('db_instance_dungeon.db', 'instancedungeon')
                            if row['Id'] == destination_id]
            if len(destinations) != 1 or type(destinations[0]['MapConfigId']) is not int:
                continue
            key = _flow(transition['CenterTextFlow'])
            text = _read(key, source) if key else None
            if not text or any(a.get('Name') != 'ShowCenterText' for a in text['source_actions']):
                continue
            sections.append({**text, 'scope': 'success_transition', 'dungeon_id': dungeon_id,
                'levelplay_id': audit['levelplay_id'], 'entry_index': tips[0][0], 'task_node_id': target['Id'],
                'source_node': deepcopy(success), 'dungeon_link': link,
                'proof': {'source_action': action, 'destination_dungeon_id': destination_id,
                          'destination_map_id': destinations[0]['MapConfigId'],
                          'relative_section_order_verified': False,
                          'runtime_verified': False}})
    for section in sections:
        section.update(placement='supplement', state_keys=[section['state_key']])
        if section['scope'] != 'before_explicit_dungeon_completion':
            continue
        later = [entry for entry in entries[section['entry_index'] + 1:] if _flow(entry.get('Flow'))]
        if not later:
            continue
        anchor = _flow(later[0]['Flow'])
        if sum(_flow(entry.get('Flow')) == anchor for entry in entries) != 1:
            continue
        indices = [index for index, event in enumerate(result.get('events', [])) if event.get('state_key') == anchor]
        if not indices or indices != list(range(indices[0], indices[-1] + 1)):
            continue
        section.update(placement='body', insert_before_event=indices[0])
        section['proof'].update(recap_after_state=anchor,
                                placement_basis='unique completed-dungeon tip precedes unique next recap flow')
    return sections
