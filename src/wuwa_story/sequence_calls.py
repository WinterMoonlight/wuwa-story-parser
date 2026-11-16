"""Validate observable sequence-call shapes without pretending to play the asset."""


def head_icon(params):
    if not isinstance(params, dict) or set(params) != {'HeadStyleConfig', 'Visible'}:
        return False
    config = params['HeadStyleConfig']
    return (isinstance(config, dict) and set(config) == {'Type', 'WhoId'}
            and type(config['Type']) is int and type(config['WhoId']) is int
            and type(params['Visible']) is bool)


def sequence_call(params):
    if not isinstance(params, dict) or set(params) - {'Path', 'ResetCamera', 'FrameEvents'}:
        return False
    if not isinstance(params.get('Path'), str) or not params['Path'].strip():
        return False
    if 'ResetCamera' in params and type(params['ResetCamera']) is not bool:
        return False
    frames = params.get('FrameEvents', [])
    if not isinstance(frames, list):
        return False
    for frame in frames:
        if not isinstance(frame, dict) or set(frame) != {'EventKey', 'EventActions'}:
            return False
        if not isinstance(frame['EventKey'], str) or not frame['EventKey'] or not isinstance(frame['EventActions'], list):
            return False
        for action in frame['EventActions']:
            if not isinstance(action, dict) or set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid'}:
                return False
            if action.get('Name') != 'ChangeEntityState':
                return False
            p = action.get('Params')
            if (not isinstance(p, dict) or set(p) != {'Type', 'EntityId', 'State'}
                    or p['Type'] != 'Directly' or type(p['EntityId']) is not int
                    or not isinstance(p['State'], str) or not p['State']):
                return False
    return True
