"""Evidence-preserving external content inspection, not runtime UI simulation."""
import hashlib
import struct
import json
from .database import string, texts, field, integer
from .paths import WORK_DIR
from .export_task import walk

TASK_EXTERNAL = {'CommonTip', 'OpenSystemBoard', 'OpenSystemFunction', 'CompleteGuide', 'GuideTrigger',
                 'SendNpcMail', 'PromptQuestChapterUI', 'TeleportDungeon', 'PhoneSystemInteract', 'SwitchSubLevels', 'SetVar', 'OpenSimpleGameplay', 'AddPlayBubble', 'SwitchDataLayers'}


def node_context(node, nodes):
    by_id = {n['Id']: n for n in nodes}
    chain, seen = [], set()
    current = node
    while current:
        if current['Id'] in seen:
            raise ValueError('Cyclic UI owner ancestry')
        seen.add(current['Id'])
        chain.append({k: current[k] for k in ('Id', 'Type', 'Condition', 'ExitCondition', 'FailedCondition', 'Count', 'DungeonId', 'DisableOnline') if k in current})
        parent = current.get('ParentNodeId', 0)
        if parent and parent not in by_id:
            raise ValueError('Missing UI owner ancestor')
        current = by_id.get(parent) if parent else None
    return {'ancestry': chain, 'route_scope': 'failure_branch' if any(n['Type'] == 'QuestFailed' for n in chain) else 'gameplay_node',
            'global_runtime_order_verified': False}


def inspect_node_ui(nodes):
    """Preserve node-owned text and visibility metadata without simulating UI."""
    records = []
    def visit(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                if key.startswith('Tid') and isinstance(child, str) and child:
                    yield path + [key], child
                else:
                    yield from visit(child, path + [key])
        elif isinstance(value, list):
            for i, child in enumerate(value):
                yield from visit(child, path + [i])
    for node in nodes:
        for root in ('TidTip', 'UIConfig', 'OccupationConfig'):
            for path, key in visit({root: node[root]} if root in node else {}, []):
                records.append({'node_id': node['Id'], 'source_path': path,
                    'context': node_context(node, nodes),
                    'visibility_flags': {k: node[k] for k in ('HideUi', 'HideTip', 'HideUiExceptTaskList') if k in node},
                    'source_config': node[root], 'text_id': key, 'raw_text': texts.get(key),
                    'missing': key not in texts, 'display_verified': False})
    return records


def inspect_task_content(nodes, read_rows, include_nested=True):
    records = []
    for node in nodes:
        for phase in ('EnterActions', 'FinishActions', 'Actions'):
            for index, action in enumerate(node.get(phase, [])):
                name, params = action['Name'], action.get('Params', {})
                if name not in TASK_EXTERNAL:
                    continue
                entry = {'node_id': node['Id'], 'node_type': node['Type'], 'phase': phase,
                         'action_index': index, 'source_action': action,
                         'route_scope': 'failure_branch' if node['Type'] == 'QuestFailed' else 'gameplay_node',
                         'preceding_actions': node.get(phase, [])[:index]}
                entry.update(node_context(node, nodes))
                entry['timing'] = {
                    'basis': 'configured_action_array_order',
                    'completion_order_verified': False,
                    'preceding_async_action_indices': [i for i, a in enumerate(entry['preceding_actions']) if a.get('Async') or a.get('Params', {}).get('Async')],
                    'following_actions': node.get(phase, [])[index + 1:]}
                if name == 'SwitchDataLayers':
                    if set(params) != {'LoadDataLayers', 'UnloadDataLayers'} or any(not isinstance(v, list) or any(type(x) is not int for x in v) for v in params.values()):
                        raise ValueError('Unsupported data layer configuration')
                    entry.update(status='data_layers_not_simulated', load_layers=params['LoadDataLayers'], unload_layers=params['UnloadDataLayers'])
                elif name == 'AddPlayBubble':
                    from .task_flows import inspect_bubble
                    bubble = inspect_bubble(params, read_rows)
                    entry.update(status='proximity_bubble_read', bubble=bubble, texts=bubble.pop('texts'))
                elif name == 'OpenSimpleGameplay':
                    from .reigns import inspect_reigns
                    if set(params) != {'GameplayConfig'}: raise ValueError('Unsupported gameplay parameters')
                    gameplay = inspect_reigns(params['GameplayConfig'], read_rows)
                    entry.update(status='gameplay_text_inventory_only', gameplay=gameplay, texts=gameplay.pop('texts'))
                elif name == 'SetVar':
                    left, right = params.get('VarLeft', {}), params.get('VarRight', {})
                    if (set(params) != {'VarLeft', 'VarRight'} or set(left) != {'Type', 'Source', 'Name'}
                            or set(right) != {'Type', 'Source', 'Value'} or left['Type'] != 'Int'
                            or left['Source'] != 'Self' or right['Type'] != 'Int' or right['Source'] != 'Constant'):
                        raise ValueError('Unsupported variable assignment')
                    readers = [{'node_id': n['Id'], 'comparison': obj} for n in nodes for obj in walk(n)
                               if obj.get('Type') == 'CompareVar' and obj.get('Var1') == left]
                    entry.update(status='variable_assignment_not_executed', variable=left, assigned_value=right['Value'], readers=readers)
                elif name == 'PhoneSystemInteract':
                    from .phone import inspect_phone
                    phone = inspect_phone(params, read_rows, preserve_unparsed=True)
                    entry.update(status='phone_body_unparsed' if phone.get('status') == 'unparsed_message_layout' else 'phone_flow_read_timing_unverified', phone=phone)
                elif name == 'SwitchSubLevels':
                    if set(params) != {'Type', 'LoadLevels', 'UnloadLevels'} or params['Type'] != 'Directly':
                        raise ValueError('Unsupported sublevel switch')
                    entry.update(status='sublevel_switch_not_simulated', load_levels=params['LoadLevels'],
                                 unload_levels=params['UnloadLevels'])
                elif name == 'SendNpcMail':
                    if set(params) != {'MailId'}:
                        raise ValueError('Unsupported mail send parameters')
                    matches = [r for r in read_rows('db_mail.db', 'mail') if r['MailId'] == params['MailId']]
                    if len(matches) != 1:
                        raise ValueError('Missing or ambiguous mail reference')
                    import base64
                    import struct
                    blob = matches[0]['BinData']
                    root = struct.unpack_from('<I', blob)[0]
                    vtable = root - struct.unpack_from('<i', blob, root)[0]
                    count = (struct.unpack_from('<H', blob, vtable)[0] - 4) // 2
                    fields = [i for i in range(count) if field(blob, i)]
                    if fields != [0] or integer(blob, 0) != params['MailId']:
                        raise ValueError('Mail schema has undecoded fields; inspect before exporting')
                    entry.update(status='mail_body_unavailable_in_row', mail_id=params['MailId'],
                        source_table='db_mail.db/mail', sha256=hashlib.sha256(blob).hexdigest(),
                        bin_data_base64=base64.b64encode(blob).decode('ascii'), present_fields=fields,
                        read_condition_nodes=[{'node_id': n['Id'], 'context': node_context(n, nodes),
                                               'condition': n['Condition']} for n in nodes
                                              if n.get('Condition', {}).get('Type') == 'ReadMail'
                                              and n['Condition'].get('MailId') == params['MailId']],
                        note='ID-only configuration row; sender, subject and body cannot be resolved from this row')
                elif name == 'PromptQuestChapterUI':
                    if set(params) != {'ChapterState'}:
                        raise ValueError('Unsupported chapter UI parameters')
                    entry.update(status='chapter_ui_unverified', chapter_state=params['ChapterState'])
                elif name == 'TeleportDungeon':
                    if set(params) - {'DungeonId', 'IsRegroup', 'LocationEntityId', 'TransitionOption'}:
                        raise ValueError('Unsupported dungeon teleport parameters')
                    transition = params.get('TransitionOption', {})
                    entry.update(status='teleport_transition_unverified', dungeon_id=params.get('DungeonId'),
                                 transition=transition, runtime_executed=False)
                elif name == 'CommonTip':
                    option = params.get('TipOption', {})
                    keys = [v for k, v in option.items() if k.startswith('Tid') and v]
                    entry['texts'] = [{'text_id': k, 'raw_text': texts.get(k), 'missing': k not in texts} for k in keys]
                    entry['status'] = 'text_references_read' if keys else 'unsupported_tip_shape'
                elif name == 'CompleteGuide':
                    entry.update(status='completion_marker_only', guide_id=params.get('GuideId'))
                elif name == 'GuideTrigger':
                    from .guides import inspect_guide
                    guide = inspect_guide(params, read_rows)
                    entry.update(status='guide_config_read_display_unverified', guide_id=params.get('GuideId'),
                                 conditions=params.get('Conditions', []), guide=guide, texts=guide.pop('texts'))
                elif name == 'OpenSystemBoard' and params.get('SystemType') == 'InformationView' and set(params) == {'SystemType', 'BoardId'}:
                    from .information_boards import inspect_information
                    board = inspect_information(params['BoardId'], read_rows)
                    entry.update(status='information_board_read', information_board=board,
                                 texts=board['texts'], board_id=params['BoardId'])
                elif name == 'OpenSystemBoard' and params.get('SystemType') == 'RoleDescription':
                    rows = [r for r in read_rows('db_roleDescription.db', 'roledescription') if r['Id'] == params['BoardId']]
                    if len(rows) != 1:
                        raise ValueError('Role description reference is not unique')
                    row = rows[0]
                    key = string(row['BinData'], 3)
                    roles = [r for r in read_rows('db_role.db', 'roleinfo') if r['Id'] == row['RoleId']]
                    if len(roles) != 1:
                        raise ValueError('Role description owner is not unique')
                    name_key = string(roles[0]['BinData'], 4)
                    entry['owner'] = {'role_id': row['RoleId'], 'name_text_id': name_key,
                                      'name': texts.get(name_key), 'source_table': 'db_role.db/roleinfo',
                                      'sha256': hashlib.sha256(roles[0]['BinData']).hexdigest()}
                    entry.update(status='description_read_ui_not_reconstructed', role_id=row['RoleId'],
                                 source_table='db_roleDescription.db/roledescription',
                                 sha256=hashlib.sha256(row['BinData']).hexdigest(),
                                 texts=[{'text_id': key, 'raw_text': texts.get(key), 'missing': key not in texts}])
                    entry['texts'].append({'text_id': name_key, 'raw_text': texts.get(name_key), 'missing': name_key not in texts, 'purpose': 'owner_name'})
                elif name == 'OpenSystemBoard' and params.get('SystemType') == 'GameSysOpen' and set(params) == {'SystemType', 'BoardId'}:
                    entry.update(status='system_board_body_unresolved', board_id=params['BoardId'],
                                 note='Invocation preserved; board body and display timing not decoded')
                elif name == 'OpenSystemFunction':
                    rows = [r for r in read_rows('db_function.db', 'functioncondition') if r['FunctionId'] == params['FunctionId']]
                    if len(rows) != 1:
                        raise ValueError('System function reference is not unique')
                    row = rows[0]
                    entry.update(status='ui_label_only', ui_label=string(row['BinData'], 1),
                                 source_table='db_function.db/functioncondition',
                                 sha256=hashlib.sha256(row['BinData']).hexdigest())
                else:
                    raise ValueError('Unsupported external content shape: ' + name)
                records.append(entry)
    # Nested guide calls retain their exact path; no execution order is inferred.
    def nested_guides(value, path):
        if isinstance(value, dict):
            if value.get('Name') == 'GuideTrigger' and 'Params' in value and len(path) > 2:
                yield path, value
            for key, child in value.items():
                yield from nested_guides(child, path + [key])
        elif isinstance(value, list):
            for i, child in enumerate(value):
                yield from nested_guides(child, path + [i])
    for node in nodes if include_nested else []:
        for path, action in nested_guides(node, []):
            from .guides import inspect_guide
            params = action['Params']
            guide = inspect_guide(params, read_rows)
            records.append({'node_id': node['Id'], 'source_path': path, 'source_action': action,
                            **node_context(node, nodes), 'status': 'guide_config_read_display_unverified',
                            'guide_id': params.get('GuideId'), 'guide': guide, 'texts': guide.pop('texts'),
                            'nested_placement_verified': False})
    # Other nested external calls still need explicit support.
    all_calls = ([a for a in walk(nodes) if a.get('Name') in TASK_EXTERNAL and 'Params' in a] if include_nested else
                 [a for n in nodes for phase in ('EnterActions', 'FinishActions', 'Actions') for a in n.get(phase, []) if a.get('Name') in TASK_EXTERNAL])
    if len(all_calls) != len(records):
        raise ValueError('Nested external task content needs placement support')
    return records


def inspect_movie(name, read_rows):
    rows = [r for r in read_rows('db_cgVedio.db', 'videodata') if r['CgName'] == name]
    female = [r for r in rows if r['GirlOrBoy'] == 0]
    if len(female) != 1:
        raise ValueError('Movie female variant is missing or ambiguous: ' + name)
    row = female[0]
    captions = [r for r in read_rows('db_cgVedio.db', 'videocaption') if r['CgName'] == name]
    asset_path = string(row['BinData'], 4)
    result = {'video_name': name, 'cg_id': row['CgId'], 'gender_code': row['GirlOrBoy'],
            'asset_path': asset_path,
            'source_table': 'db_cgVedio.db/videodata', 'sha256': hashlib.sha256(row['BinData']).hexdigest(),
            'caption_row_count': len(captions),
            'caption_status': 'rows_require_decoding' if captions else 'no_rows_not_proof_of_silence',
            'text_coverage': 'known_caption_rows_unparsed' if captions else 'additional_text_unverified',
            'note': 'Caption rows require decoding' if captions else 'No matching caption rows; additional dialogue or subtitles are neither confirmed nor ruled out'}
    if captions:
        from .captions import decode_captions
        try:
            result.update(decode_captions(name, captions))
            result['caption_status'] = 'text_read_consensus_order' if result['caption_order_consensus'] else 'text_read_order_unverified'
            result['text_coverage'] = 'configured_captions_read'
            result['note'] = 'Configured text extracted; timing units, track languages, speaker identity and extra on-screen text unverified'
        except (ValueError, TypeError, KeyError, IndexError, struct.error) as exc:
            result['caption_decode_error'] = str(exc)
    result['sound_sources'] = [
        {'source_table': 'db_cgVedio.db/videosound', 'row_id': r['CaptionId'],
         'gender_code': r['GirlOrBoy'], 'audio_event': string(r['BinData'], 3),
         'sha256': hashlib.sha256(r['BinData']).hexdigest(),
         'text_decoded': False}
        for r in read_rows('db_cgVedio.db', 'videosound') if r['CgName'] == name]
    result['silence_verified'] = False
    # Optional exported properties are evidence, never instructions or URLs to fetch.
    package, _, object_name = asset_path.rpartition('.')
    properties = WORK_DIR / 'asset_exports' / 'properties' / (object_name + '.json')
    if object_name and '/' not in object_name and '\\' not in object_name and properties.is_file():
        data = json.loads(properties.read_text(encoding='utf-8-sig'))
        expected_package = package.replace('/Game/', 'Client/Content/', 1)
        matches = [o for o in data if isinstance(o, dict) and o.get('Name') == object_name
                   and o.get('Package') == expected_package and o.get('Type') == 'StreamMediaSource'] if isinstance(data, list) else []
        if len(matches) == 1:
            result['media_source_evidence'] = {
                'type': 'StreamMediaSource', 'stream_url': matches[0].get('Properties', {}).get('StreamUrl'),
                'properties_file': str(properties.relative_to(WORK_DIR)).replace('\\', '/'),
                'sha256': hashlib.sha256(properties.read_bytes()).hexdigest(),
                'meaning': 'Media locator only; does not establish whether the referenced media contains text'}
    return result
