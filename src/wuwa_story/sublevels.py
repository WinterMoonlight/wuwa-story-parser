"""Retain sublevel switch configuration without simulating streaming completion."""


def switch_shape(action):
    if (action.get('Name') != 'SwitchSubLevels' or action.get('Async', False) is not False
            or set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}):
        return False
    p = action.get('Params')
    if not isinstance(p, dict) or not {'Type', 'LoadLevels', 'UnloadLevels'} <= set(p) <= {
            'Type', 'LoadLevels', 'UnloadLevels', 'TeleportEntityId', 'IsWaitForSwitchComplete'}:
        return False
    if p['Type'] != 'Directly':
        return False
    for k in ('LoadLevels', 'UnloadLevels'):
        if not isinstance(p[k], list) or not all(isinstance(v, str) and v.startswith('/Game/') for v in p[k]):
            return False
    return (('TeleportEntityId' not in p or type(p['TeleportEntityId']) is int)
            and ('IsWaitForSwitchComplete' not in p or type(p['IsWaitForSwitchComplete']) is bool))


def switch_evidence(action):
    p = action['Params']
    return {'source_action': action, 'load_levels': p['LoadLevels'], 'unload_levels': p['UnloadLevels'],
            'teleport_entity_id': p.get('TeleportEntityId'),
            'wait_for_completion': p.get('IsWaitForSwitchComplete'),
            'wait_flag_present': 'IsWaitForSwitchComplete' in p,
            'streaming_completion_verified': False, 'callbacks_verified': False,
            'note': 'Configuration call order only; omitted wait flag has unknown default; streaming and callbacks not simulated'}
