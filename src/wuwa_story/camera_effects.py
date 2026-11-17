"""Explicit camera payloads accepted for reading; no runtime camera simulation."""
import math

CAMERA_EFFECTS = {'PlayerLookAt', 'RestorePlayerCameraAdjustment', 'ResetPlayerCameraFocus', 'AdjustPlayerCamera'}


def camera_shape(action):
    if (action.get('Async', False) is not False or
            set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async', 'Timeout'}):
        return False
    if 'Timeout' in action and (type(action['Timeout']) not in (int, float)
            or not math.isfinite(action['Timeout']) or action['Timeout'] < 0):
        return False
    p = action.get('Params', {})
    if not isinstance(p, dict):
        return False
    number = lambda v: type(v) in (int, float) and math.isfinite(v)
    def vector(v):
        return isinstance(v, dict) and bool(v) and set(v) <= {'X', 'Y', 'Z'} and all(number(x) for x in v.values())
    def curve(v):
        return (isinstance(v, dict) and set(v) == {'Type', 'N'} and type(v['Type']) is int
                and v['Type'] in {1, 2, 4} and number(v['N']) and v['N'] > 0)
    name = action.get('Name')
    if name == 'RestorePlayerCameraAdjustment':
        if p == {}:
            return True
        v = p.get('ResetFocus')
        return (set(p) == {'ResetFocus'} and isinstance(v, dict) and set(v) == {'FadeInTime', 'FadeInCurve'}
                and number(v['FadeInTime']) and v['FadeInTime'] >= 0 and curve(v['FadeInCurve']))
    if name == 'AdjustPlayerCamera':
        o = p.get('Option')
        if set(p) != {'Option'} or not isinstance(o, dict):
            return False
        base = {'Type', 'Priority', 'FadeInTime', 'FadeOutTime', 'ArmLength', 'MinumArmLength', 'MaxiumArmLength', 'Offset', 'Fov'}
        if o.get('Type') == '关卡.Common.镜头.对话镜头':
            required = base | {'CenterPos', 'YawAngle', 'PitchAngle'}
            optional = {'FadeInCurve', 'FadeOutCurve'}
        elif o.get('Type') == '关卡.Common.镜头调整':
            required = base | {'OverlayArmLength'}
            optional = {'FadeInCurve', 'FadeOutCurve', 'PitchLimitMin', 'PitchLimitMax',
                        'YawLimitMin', 'YawLimitMax', 'IsDisableCollision', 'IsDisableDither'}
        else:
            return False
        if not required <= set(o) <= required | optional:
            return False
        for k, v in o.items():
            if k == 'Type': continue
            if k in {'Offset', 'CenterPos'}:
                if not vector(v): return False
            elif k.endswith('Curve'):
                if not curve(v): return False
            elif k.startswith('Is'):
                if type(v) is not bool: return False
            elif not number(v): return False
        return o['FadeInTime'] >= 0 and o['FadeOutTime'] >= 0 and 0 < o['Fov'] < 180
    if name == 'ResetPlayerCameraFocus':
        return (set(p) == {'FadeInTime', 'ResetType'} and number(p['FadeInTime'])
                and p['FadeInTime'] >= 0 and p['ResetType'] == {'Type': 'ResetToDefaultDirection'})
    if name == 'PlayerLookAt':
        pos = p.get('Pos')
        return ({'Pos', 'CameraMove'} <= set(p) <= {'Pos', 'CameraMove', 'PlayAnimation'}
                and ('PlayAnimation' not in p or type(p['PlayAnimation']) is bool)
                and type(p['CameraMove']) is bool
                and isinstance(pos, dict) and set(pos) == {'X', 'Y', 'Z'}
                and all(number(v) for v in pos.values()))
    return False
