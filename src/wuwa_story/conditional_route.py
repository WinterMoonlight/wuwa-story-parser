"""A scoped, satisfiable reading path through one Boolean-guarded menu."""
from copy import deepcopy
from hashlib import sha256

from .combined_information import ACTION_FIELDS, jump_target
from .database import embedded, texts
from .terminal_text import synchronous
from .variables import compare_var_shape, set_var_shape


def guard_atom(guard):
    if not isinstance(guard, dict) or set(guard) != {'Type', 'Conditions'} or guard['Type'] != 'Condition':
        raise ValueError('Unknown conditional menu envelope')
    group = guard['Conditions']
    if (not isinstance(group, dict) or set(group) != {'Type', 'Conditions'}
            or group['Type'] != 0 or not isinstance(group['Conditions'], list)
            or len(group['Conditions']) != 1):
        raise ValueError('Conditional route needs one Boolean guard')
    atom = group['Conditions'][0]
    if not compare_var_shape(atom) or atom['Var1']['Source'] != 'Self':
        raise ValueError('Conditional route needs a Self Boolean equality')
    return atom


def owner_evidence(key, read_rows):
    from .export_task import flow_key
    family = key.rsplit('_', 2)[0].encode('utf-8')
    matches = []
    for row in read_rows('db_level_entity.db', 'levelentityconfig'):
        if family not in row['BinData']:
            continue
        configs = [value for _, value in embedded(row['BinData']) if isinstance(value, dict)]
        if not configs or any(value != configs[0] for value in configs):
            continue
        for option in configs[0].get('InteractComponent', {}).get('Options', []):
            kind = option.get('Type', {})
            ref = kind.get('Flow', {})
            if (kind.get('Type') == 'Flow' and set(ref) == {'FlowListName', 'FlowId', 'StateId'}
                    and flow_key(ref) == key):
                matches.append((row, configs[0], option))
    if len(matches) != 1:
        raise ValueError('Conditional route owner is not unique')
    row, config, option = matches[0]
    condition = option.get('Condition', {})
    if (set(condition) != {'Type', 'Conditions'} or condition['Type'] != 0
            or not isinstance(condition['Conditions'], list) or len(condition['Conditions']) != 1):
        raise ValueError('Unsupported entity entry condition')
    atom = condition['Conditions'][0]
    if (set(atom) != {'Type', 'Var1', 'Compare', 'Var2'} or atom['Type'] != 'CompareVar'
            or atom['Compare'] != 'Gt'
            or set(atom['Var1']) != {'Type', 'Source', 'Name'}
            or atom['Var1']['Type'] != 'Int' or atom['Var1']['Source'] != 'Self'
            or set(atom['Var2']) != {'Type', 'Source', 'Value'}
            or atom['Var2']['Type'] != 'Int' or atom['Var2']['Source'] != 'Constant'
            or type(atom['Var2']['Value']) is not int):
        raise ValueError('Unsupported entity entry predicate')
    variables = config.get('VarComponent', {}).get('Vars', [])
    initial = {(v['Type'], v['Name']): v['Value'] for v in variables}
    if len(initial) != len(variables):
        raise ValueError('Ambiguous initial variables')
    value = initial.get(('Int', atom['Var1']['Name']))
    if type(value) is not int or value <= atom['Var2']['Value']:
        raise ValueError('No declared witness for entity entry')
    return row, condition, initial


def visual_target(action, owner, read_rows):
    params = action.get('Params', {})
    if (set(params) != {'Type', 'EntityId', 'State'} or params['Type'] != 'Directly'
            or type(params['EntityId']) is not int or not isinstance(params['State'], str)):
        raise ValueError('Unsupported conditional entity transition')
    rows = [r for r in read_rows('db_level_entity.db', 'levelentityconfig')
            if r['MapId'] == owner['MapId'] and r['EntityId'] == params['EntityId']]
    if len(rows) != 1:
        raise ValueError('Ambiguous conditional entity target')
    row = rows[0]
    configs = [v for _, v in embedded(row['BinData']) if isinstance(v, dict)]
    if not configs or any(v != configs[0] for v in configs):
        raise ValueError('Ambiguous target configuration')
    config = configs[0]
    if set(config) != {'BaseInfoComponent', 'EntityStateComponent', 'SceneActorRefComponent'}:
        raise ValueError('Target has additional behavior')
    if (set(config['BaseInfoComponent']) - {'PackId', 'IsForceDestroy'}
            or set(config['EntityStateComponent']) != {'Type', 'State'}
            or set(config['SceneActorRefComponent']) != {'ActorRefGroups'}):
        raise ValueError('Target contains unreviewed component fields')
    groups = config['SceneActorRefComponent']['ActorRefGroups']
    if sum(g['EntityState'] == params['State'] for g in groups) != 1:
        raise ValueError('Target state is not unique')
    for group in groups:
        if set(group) != {'EntityState', 'Actions'}:
            raise ValueError('Unknown actor callback group')
        for callback in group['Actions']:
            p = callback.get('Params', {})
            if (not synchronous(callback, 'EnableActor') or set(p) != {'ActorType', 'Enable', 'Targets'}
                    or p['ActorType'] != 'MeshActor' or type(p['Enable']) is not bool
                    or not isinstance(p['Targets'], list)
                    or any(not isinstance(t, dict) or set(t) != {'PathName'} for t in p['Targets'])):
                raise ValueError('Target callback may affect dialogue')
    return {'map_id': row['MapId'], 'entity_id': row['EntityId'],
            'sha256': sha256(row['BinData']).hexdigest(),
            'declared_callbacks_visual_only': True, 'runtime_executed': False}


def build_route(actions, key, menu, option_index, owner, entry, initial, source, names, choices):
    from .export_task import Exporter, walk
    show_index = next(i for i, a in enumerate(actions) if a['Name'] == 'ShowTalk')
    show = actions[show_index]
    items = show['Params']['TalkItems']
    positions = {item['Id']: i for i, item in enumerate(items)}
    option = menu['Options'][option_index]
    atom = guard_atom(option['PreCondition'])
    name, value = atom['Var1']['Name'], atom['Var2']['Value']
    if type(initial.get(('Boolean', name))) is not bool or initial[('Boolean', name)] != value:
        raise ValueError('Selected guard lacks a declared satisfiability witness')
    symbols = {name: {'kind': 'path_assumption', 'value': value}}
    projected, selected_ids, effects = [], [], []
    position, selected, ended = 0, False, False
    while position < len(items):
        item = items[position]
        if item['Id'] in selected_ids:
            raise ValueError('Conditional route contains a loop')
        if (item.get('Type') != 'Talk' or item.get('TidTalk') not in texts
                or any('condition' in k.lower() for k in item)):
            raise ValueError('Conditional route contains unsupported text or conditions')
        selected_ids.append(item['Id'])
        projected_item = deepcopy(item)
        target = None
        if item.get('Options'):
            if selected or item is not menu or item.get('Actions'):
                raise ValueError('Conditional route contains another menu')
            selected = True
            target = jump_target(option.get('Actions'))
            if target not in positions or option.get('TidTalkOption') not in texts:
                raise ValueError('Selected option has no valid local jump or text')
            projected_option = deepcopy(option)
            projected_option.pop('PreCondition')
            projected_item['Options'] = [projected_option]
        retained = []
        for action_index, action in enumerate(item.get('Actions', [])):
            if set(action) - ACTION_FIELDS or not synchronous(action, action.get('Name')):
                raise ValueError('Unknown conditional action metadata')
            kind, params = action['Name'], action.get('Params', {})
            effect = {'after_talk_id': item['Id'], 'source_action': deepcopy(action), 'runtime_executed': False}
            if kind == 'SetVar' and set_var_shape(action) and params['VarLeft']['Source'] == 'Self':
                var = params['VarLeft']['Name']
                effect.update(before=deepcopy(symbols.get(var, {'kind': 'unknown'})),
                              after={'kind': 'constant', 'value': params['VarRight']['Value']})
                symbols[var] = effect['after']
            elif kind == 'CalculateVar':
                if (set(params) != {'Var1', 'Var2', 'Op', 'Result'} or params['Op'] != 'Sub'
                        or params['Var1'] != params['Result']
                        or set(params['Var1']) != {'Type', 'Source', 'Name'}
                        or params['Var1']['Type'] != 'Int' or params['Var1']['Source'] != 'Self'
                        or set(params['Var2']) != {'Type', 'Source', 'Value'}
                        or params['Var2']['Type'] != 'Int' or params['Var2']['Source'] != 'Constant'
                        or type(params['Var2']['Value']) is not int):
                    raise ValueError('Unsupported conditional arithmetic')
                effect['after'] = {'kind': 'symbolic_subtraction', 'entry_symbol': params['Var1']['Name'],
                                   'subtract': params['Var2']['Value']}
            elif kind == 'ChangeEntityState':
                effect['target'] = visual_target(action, owner, source.rows)
            elif kind == 'FinishTalk' and params == {} and action_index == len(item['Actions']) - 1:
                retained.append(action)
                ended = True
                continue
            else:
                raise ValueError('Unsupported conditional route action')
            effects.append(effect)
        if 'Actions' in projected_item:
            projected_item['Actions'] = retained
        projected.append(projected_item)
        if ended:
            break
        position = positions[target] if target is not None else position + 1
    if not selected:
        raise ValueError('Conditional menu was not reached')
    # Side effects may be audited away only when later selected text/control
    # cannot read them, including actions later in the same Talk item.
    for effect in effects:
        action = effect['source_action']
        if action['Name'] not in {'SetVar', 'CalculateVar'}:
            continue
        reference = action['Params']['VarLeft' if action['Name'] == 'SetVar' else 'Result']
        item = items[positions[effect['after_talk_id']]]
        action_index = item['Actions'].index(action)
        tail = [item['Actions'][action_index + 1:],
                [items[positions[i]] for i in selected_ids[selected_ids.index(item['Id']) + 1:]],
                actions[show_index + 1:]]
        if any(o.get('Source') == reference['Source'] and o.get('Name') == reference['Name']
               for o in walk(tail)):
            raise ValueError('A later action reads an audited variable')
    projection = deepcopy(actions)
    projection[show_index]['Params']['TalkItems'] = projected
    parser = Exporter(source=source, allow_incomplete=True, speaker_records=names, choices=choices)
    parser.state_key = key
    if parser.actions(projection) or parser.missing:
        raise ValueError('Conditional projection did not finish')
    originals = {item['Id']: item for item in items}
    for event in parser.events:
        if event['kind'] == 'dialogue':
            event['source_item'] = deepcopy(originals[event['talk_id']])
        elif event['kind'] == 'choice':
            event.update(selected_index=option_index, source_option=deepcopy(option))
    decision = parser.decisions[0]
    decision['selected_index'] = option_index
    decision['options'] = [{'text_id': o['TidTalkOption'], 'text': texts[o['TidTalkOption']],
                            'actions': deepcopy(o['Actions']), 'source_condition': deepcopy(o['PreCondition']),
                            'availability': 'conditional'} for o in menu['Options']]
    parser.unverified_content.append({'kind': 'conditional_text_route',
        'choice_key': decision['choice_key'], 'selected_original_index': option_index,
        'entry_requirements': [deepcopy(entry), deepcopy(option['PreCondition'])],
        'owner': {'map_id': owner['MapId'], 'entity_id': owner['EntityId'],
                  'sha256': sha256(owner['BinData']).hexdigest()},
        'satisfiability_witness': [{'type': t, 'name': n, 'value': v} for (t, n), v in initial.items()],
        'witness_is_current_state': False, 'symbolic_effects': effects,
        'talk_ids': selected_ids, 'local_text_order_verified': True,
        'end_basis': 'FinishTalk' if ended else 'array_end',
        'all_branch_actions_verified': False, 'runtime_route_verified': False,
        'cross_segment_variable_propagation': False})
    return parser


def conditional_text_route(actions, key, source, names, choices=None):
    """Return a complete conditional reading path, or retain the old boundary."""
    if source is None:
        return None
    try:
        calls = [a for a in actions if a.get('Name') == 'ShowTalk']
        if (len(calls) != 1 or not synchronous(calls[0], 'ShowTalk')
                or set(calls[0]['Params']) != {'TalkItems'}):
            return None
        index = actions.index(calls[0])
        if any(a.get('Name') not in {'SetPlotMode', 'BeginFlowTemplate'} for a in actions[:index]):
            return None
        if any(not synchronous(a, 'CloseFlowTemplate') for a in actions[index + 1:]):
            return None
        items = calls[0]['Params']['TalkItems']
        if (not isinstance(items, list) or not items or any(type(i.get('Id')) is not int for i in items)
                or len({i['Id'] for i in items}) != len(items)):
            return None
        menus = [item for item in items if item.get('Options')]
        if len(menus) != 1:
            return None
        menu = menus[0]
        for option in menu['Options']:
            guard_atom(option['PreCondition'])
        owner, entry, initial = owner_evidence(key, source.rows)
        choice_key = f'{key}:{menu["Id"]}'
        explicit = (choices or {}).get(choice_key)
        if explicit is not None and (type(explicit) is not int or not 0 <= explicit < len(menu['Options'])):
            return None
        candidates = [explicit] if explicit is not None else range(len(menu['Options']))
        for selected in candidates:
            try:
                # Projection has a single option, retaining the original index in evidence.
                overrides = dict(choices or {})
                overrides[choice_key] = 0
                return build_route(actions, key, menu, selected, owner, entry, initial, source, names, overrides)
            except (ValueError, KeyError, TypeError, IndexError, AttributeError):
                continue
    except (ValueError, KeyError, TypeError, IndexError, AttributeError):
        return None
    return None
