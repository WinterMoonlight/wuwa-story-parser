"""Narrow item/option combinations with no competing option-side action."""
import math


def single_passive_option(item):
    options = item.get('Options')
    return (item.get('Type') == 'Talk' and isinstance(options, list) and len(options) == 1
            and isinstance(options[0], dict)
            and set(options[0]) <= {'TidTalkOption', 'Actions', 'TextId', 'PlotLineId', 'PlotLineKey'}
            and all(type(options[0][k]) is int for k in ('TextId', 'PlotLineId') if k in options[0])
            and ('PlotLineKey' not in options[0] or isinstance(options[0]['PlotLineKey'], str))
            and isinstance(options[0].get('TidTalkOption'), str)
            and bool(options[0]['TidTalkOption']) and options[0].get('Actions', []) == [])


def hide_range_shape(action):
    if (not isinstance(action, dict) or action.get('Name') != 'HideByRangeInFlow'
            or set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            or action.get('Async', False) is not False):
        return False
    p = action.get('Params')
    if not isinstance(p, dict) or set(p) != {'Center', 'Radius', 'EntityIds', 'IsCleanSimpleNpc', 'IsCleanPasserByNpc'}:
        return False
    number = lambda v: type(v) in (int, float) and math.isfinite(v)
    return (isinstance(p['Center'], dict) and set(p['Center']) == {'X', 'Y', 'Z'}
            and all(number(v) for v in p['Center'].values())
            and number(p['Radius']) and p['Radius'] > 0
            and isinstance(p['EntityIds'], list) and bool(p['EntityIds'])
            and all(type(v) is int and v > 0 for v in p['EntityIds'])
            and type(p['IsCleanSimpleNpc']) is bool and type(p['IsCleanPasserByNpc']) is bool)


def combined_hide(item):
    return (single_passive_option(item) and isinstance(item.get('Actions'), list)
            and len(item['Actions']) == 1 and hide_range_shape(item['Actions'][0]))


def combined_actor(item, items, speaker_records):
    from .speakers import anonymous
    if not single_passive_option(item) or not isinstance(item.get('Actions'), list) or len(item['Actions']) != 1:
        return False
    if not all(i.get('Type') == 'Talk' and type(i.get('WhoId')) is int and i['WhoId'] >= 0 for i in items):
        return False
    name = speaker_records.get(item['WhoId'], {}).get('name', '')
    if not name or anonymous(name):
        return False
    a = item['Actions'][0]
    if (a.get('Name') != 'ChangeActorTalker' or a.get('Async', False) is not False
            or set(a) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}):
        return False
    p = a.get('Params')
    return (isinstance(p, dict) and set(p) == {'ActorIndex', 'Talker'}
            and type(p['ActorIndex']) is int and p['ActorIndex'] >= 0
            and type(p['Talker']) is int and p['Talker'] > 0)


def evidence(item, kind):
    return {'kind': kind, 'talk_id': item['Id'], 'source_actions': item['Actions'],
            'item_action_option_relative_timing_verified': False, 'runtime_executed': False,
            'indirect_trigger_effects_verified': False,
            'note': 'Single passive option; preserve text structure, not presentation timing or runtime reachability'}
