"""Retry an implicit choice using a completely parsed local dialogue route."""
from copy import deepcopy

from .prefix_boundary import UnresolvedControlBoundary
from .combined_information import jump_target


def retry_unconditional_choice(actions, failed_parser, error, source, names, choices):
    from .export_task import Exporter, walk
    if (not isinstance(error, UnresolvedControlBoundary)
            or error.source_action.get('Name') != 'SetVar' or not failed_parser.decisions):
        return None
    if any(any('condition' in key.lower() for key in obj) for obj in walk(actions)):
        return None
    decision = failed_parser.decisions[-1]
    choice_key = decision['choice_key']
    if choice_key in (choices or {}) or decision.get('visit') != 1:
        return None
    menus = [item for item in walk(actions) if item.get('Id') == failed_parser.current_talk_id
             and item.get('Options') and item.get('Type') in {'Talk', 'Option'}]
    if len(menus) != 1 or decision.get('selected_index') is None:
        return None
    menu = menus[0]
    if choice_key != f'{failed_parser.state_key}:{menu["Id"]}':
        return None
    if menu.get('Actions'):
        return None
    original_index = decision['selected_index']
    if type(original_index) is not int or not 0 <= original_index < len(menu['Options']):
        return None
    if error.source_action not in menu['Options'][original_index].get('Actions', []):
        return None
    owners = [obj for obj in walk(actions) if obj.get('Name') == 'ShowTalk'
              and any(item is menu for item in obj.get('Params', {}).get('TalkItems', []))]
    if len(owners) != 1 or owners[0].get('Async', False) is not False:
        return None
    if set(owners[0]) - {'Name','Params','ActionId','ActionGuid','Async'}:
        return None
    for index, option in enumerate(menu['Options']):
        if index == decision['selected_index'] or jump_target(option.get('Actions')) is None:
            continue
        overrides = dict(choices or {})
        overrides[choice_key] = index
        parser = Exporter(source=source, allow_incomplete=True, speaker_records=names, choices=overrides)
        parser.state_key = failed_parser.state_key
        try:
            control = parser.actions(actions)
        except (ValueError, KeyError, TypeError, IndexError):
            continue
        if control or parser.missing or any(event['kind'] in {'unparsed_content', 'recap_gap'} for event in parser.events):
            continue
        selections = [entry for entry in parser.decisions if entry['choice_key'] == choice_key]
        if len(selections) != 1 or selections[0]['selected_index'] != index or selections[0]['visit'] != 1:
            continue
        old_prefix = [(d['choice_key'],d['selected_index']) for d in failed_parser.decisions[:-1]]
        new_prefix = [(d['choice_key'],d['selected_index']) for d in parser.decisions[:len(old_prefix)]]
        if old_prefix != new_prefix:
            continue
        from .rendering import render_result
        original_prefix = render_result({'title': '', 'route': {'choices': []},
                                         'events': deepcopy(failed_parser.events)})['events']
        parser.unverified_content.append({
            'kind': 'implicit_choice_retry', 'choice_key': choice_key,
            'original_selected_index': decision['selected_index'], 'selected_index': index,
            'original_error': str(error), 'original_boundary': error.as_dict(),
            'original_prefix_events': original_prefix,
            'explicit_override_preserved': True, 'runtime_route_verified': False,
            'cross_segment_variable_propagation': False,
            'scope': 'complete local configuration dialogue through an unconditional alternative'})
        return parser
    return None
