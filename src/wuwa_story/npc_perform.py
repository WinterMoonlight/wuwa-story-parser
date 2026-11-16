"""Reading support for inspected scalar NPC group performance calls."""


def npc_perform_shape(action):
    if (action.get('Name') != 'FlowDefineNpcGroupPerform'
            or set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            or action.get('Async', False) is not False):
        return False
    params = action.get('Params')
    if not isinstance(params, dict) or set(params) != {'PerformType'}:
        return False
    value = params['PerformType']
    if not isinstance(value, dict) or set(value) != {'Type', 'Key'}:
        return False
    kind, key = value['Type'], value['Key']
    return (type(kind) is int and isinstance(key, str)
            and ((kind in {0, 7} and bool(key.strip())) or (kind == 1 and key == '')))
