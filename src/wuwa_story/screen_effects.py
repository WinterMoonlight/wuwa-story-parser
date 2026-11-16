"""Record an explicit screen-effect stop; never synthesize asset text."""


def screen_stop_shape(action):
    if (action.get('Name') != 'StopUiScreenEffect' or action.get('Async', False) is not False
            or set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}):
        return False
    p = action.get('Params')
    return (isinstance(p, dict) and set(p) == {'EffectDaPath'}
            and isinstance(p['EffectDaPath'], str) and p['EffectDaPath'].startswith('/Game/')
            and len(p['EffectDaPath']) > len('/Game/'))
