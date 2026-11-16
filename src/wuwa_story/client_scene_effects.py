"""Read inspected client scene calls without simulating their completion."""
import math


CLIENT_SCENE_EFFECTS = {'ClientPreEnableSubLevels', 'GiantToggleModel'}


def _asset_path(value):
    return isinstance(value, str) and value.startswith('/Game/') and len(value) > 6


def client_scene_shape(action):
    if (action.get('Name') not in CLIENT_SCENE_EFFECTS
            or set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            or action.get('Async', False) is not False):
        return False
    params = action.get('Params')
    if not isinstance(params, dict):
        return False
    if action['Name'] == 'GiantToggleModel':
        return set(params) == {'IsEnabled'} and type(params['IsEnabled']) is bool
    if not {'EnableLevels', 'DisableLevels'} <= set(params) <= {
            'EnableLevels', 'DisableLevels', 'TransitionOption'}:
        return False
    for key in ('EnableLevels', 'DisableLevels'):
        if not isinstance(params[key], list) or not all(_asset_path(v) for v in params[key]):
            return False
    if 'TransitionOption' not in params:
        return True
    transition = params['TransitionOption']
    if (not isinstance(transition, dict)
            or set(transition) != {'Type', 'DelayTime', 'SceneCaptureEffect'}
            or transition['Type'] != 'SceneCapture'):
        return False
    delay = transition['DelayTime']
    return (type(delay) in (int, float) and math.isfinite(delay) and delay >= 0
            and _asset_path(transition['SceneCaptureEffect']))


def client_scene_evidence(action):
    """The caller must validate first; no path or duration is executed."""
    params = action['Params']
    record = {'source_action': action, 'callbacks_verified': False,
              'asset_content_verified': False, 'runtime_completion_verified': False,
              'order_scope': 'explicit_configuration_only'}
    if action['Name'] == 'GiantToggleModel':
        record.update(kind='giant_model_toggle', enabled=params['IsEnabled'],
                      note='Model toggle recorded; world state and implicit callbacks not simulated')
    else:
        record.update(kind='client_sublevel_pre_enable', enable_levels=params['EnableLevels'],
                      disable_levels=params['DisableLevels'], transition=params.get('TransitionOption'),
                      wait_semantics_verified=False,
                      note='Client scene request retained; transition delay is not proof of streaming completion')
    return record
