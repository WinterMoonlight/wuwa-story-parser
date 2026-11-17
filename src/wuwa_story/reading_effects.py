"""Inspected scalar world effects for recap projection, never runtime simulation."""
READING_EFFECTS = {'HideGroup', 'SetAudioState'}

FLOW_LOCK_EFFECTS = {'SetTimeLockState', 'SetWeatherLockState'}
ENTITY_LOCK_EFFECTS = {'LockEntity', 'UnlockEntity'}


def leisure_sit_shape(action):
    if not isinstance(action, dict):
        return False
    p = action.get('Params')
    return (action.get('Name') == 'LeisureInteract'
            and set(action) <= {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            and action.get('Async', False) is False
            and isinstance(p, dict) and set(p) == {'Option', 'SceneEntity'}
            and p['Option'] == {'Type': 'SitDown'}
            and type(p['SceneEntity']) is int and p['SceneEntity'] > 0)


def entity_lock_shape(action):
    if not isinstance(action, dict):
        return False
    params = action.get('Params')
    return (action.get('Name') in ENTITY_LOCK_EFFECTS
            and set(action) <= {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            and action.get('Async', False) is False
            and isinstance(params, dict) and set(params) == {'EntityIds'}
            and isinstance(params['EntityIds'], list) and bool(params['EntityIds'])
            and all(type(i) is int and i > 0 for i in params['EntityIds']))


def flow_lock_shape(action):
    return (action.get('Name') in FLOW_LOCK_EFFECTS
            and not set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            and action.get('Async', False) is False
            and action.get('Params') in ({'LockState': 'Lock'}, {'LockState': 'Unlock'}))


def flow_audio_state_shape(action):
    if (action.get('Name') != 'SetAudioState' or action.get('Async', False) is not False
            or set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}):
        return False
    try:
        return validate_reading_effect('SetAudioState', action.get('Params', {}))
    except ValueError:
        return False


def validate_reading_effect(name, params):
    if name not in READING_EFFECTS:
        return False
    valid = isinstance(params, dict)
    if valid and name == 'SetAudioState':
        cfg = params.get('AudioConfig')
        valid = (set(params) == {'AudioConfig'} and isinstance(cfg, dict)
                 and set(cfg) == {'Group', 'State'}
                 and all(isinstance(cfg[k], str) and cfg[k] for k in cfg))
    elif valid:
        cfg = params.get('HideConfig')
        valid = (set(params) in ({'GroupKey', 'HideConfig'},
                                {'GroupKey', 'HideConfig', 'IsHidePasserByNpc'})
                 and isinstance(params.get('GroupKey'), str) and bool(params['GroupKey'])
                 and ('IsHidePasserByNpc' not in params or type(params['IsHidePasserByNpc']) is bool)
                 and isinstance(cfg, dict))
        if valid:
            kind = cfg.get('Type')
            if kind == 'SpecifyEntity':
                valid = set(cfg) == {'Type', 'EntityIds'}
            elif kind == 'WorldMonsterAndMonsterTreasure':
                valid = set(cfg) == {'Type', 'HideRangeEntities'}
            elif kind == 'WorldEntityAndLevelPlay':
                valid = ({'Type', 'HideRangeEntities'} <= set(cfg)
                         <= {'Type', 'HideRangeEntities', 'AppendEntities', 'AppendLevelPlays',
                             'ExcludeEntities', 'ExcludeLevelPlays'})
            else:
                valid = False
            valid = valid and all(isinstance(v, list) and all(type(i) is int for i in v)
                                  for k, v in cfg.items() if k != 'Type')
    if not valid:
        raise ValueError('Unsupported reading effect parameters: ' + name)
    return True


def effect_evidence(name, params):
    return {'name': name, 'params': params, 'runtime_executed': False,
            'direct_text_or_flow_payload': False,
            'indirect_trigger_effects_verified': False,
            'handling': 'recap_projection_only',
            'note': 'World visibility/audio state may affect runtime triggers; no reachability claim'}
