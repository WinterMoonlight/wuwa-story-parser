"""Retain reached dialogue before a menu or an unresolved panel call."""
from copy import deepcopy

from .combined_presentation import single_passive_option
from .terminal_text import synchronous
from .unconditional_options import candidate_indices


def conditional_menu_prefix(action, text_map):
    if not synchronous(action, 'ShowTalk'):
        return None
    params = action.get('Params')
    if not isinstance(params, dict) or set(params) - {'TalkItems', 'TalkOutline'}:
        return None
    items = params.get('TalkItems')
    if not isinstance(items, list) or not items or not all(isinstance(item, dict) for item in items):
        return None
    ids = [item.get('Id') for item in items]
    if any(type(value) is not int for value in ids) or len(set(ids)) != len(ids):
        return None
    prefix = []
    for item in items:
        if (item.get('Type') != 'Talk' or item.get('Actions')
                or any('condition' in key.lower() for key in item)
                or item.get('TidTalk') not in text_map):
            return None
        prefix.append(item)
        options = item.get('Options', [])
        if not options:
            continue
        try:
            if candidate_indices(options):
                return None
        except ValueError:
            return None
        if not options or any('PreCondition' not in option for option in options):
            return None
        projected = deepcopy(prefix)
        projected[-1].pop('Options', None)
        return projected, item
    return None


def enrollment_boundary(item):
    if not single_passive_option(item):
        return None
    actions = item.get('Actions')
    if not isinstance(actions, list) or len(actions) != 1:
        return None
    action = actions[0]
    if (not synchronous(action, 'OpenSystemBoard')
            or action.get('Params') != {'SystemType': 'Enrollment', 'BoardId': 0}):
        return None
    return action


def _enrollment_parser(actions, boundary, source, names, choices, include_suffix=False):
    """Parse static dialogue under an explicit assumption that the panel returns."""
    from .export_task import Exporter, walk
    calls = [(index, action) for index, action in enumerate(actions) if action.get('Name') == 'ShowTalk']
    if len(calls) != 1:
        return None
    index, show = calls[0]
    params = show.get('Params', {})
    if not synchronous(show, 'ShowTalk') or set(params) - {'TalkItems', 'TalkOutline'}:
        return None
    items = params.get('TalkItems', [])
    matches = [item for item in items if enrollment_boundary(item)]
    if len(matches) != 1 or matches[0] != boundary.source_item:
        return None
    for item in items:
        if item.get('Type') not in {'Talk', 'Option'}:
            return None
        for obj in walk(item):
            if any('condition' in key.lower() for key in obj):
                return None
            if 'Name' in obj and 'Params' in obj:
                if obj == boundary.source_action:
                    continue
                if not synchronous(obj, obj['Name']) or obj['Name'] not in {'JumpTalk', 'FinishTalk'}:
                    return None
    suffix_actions = {'FadeInScreen', 'FadeOutScreen', 'CloseFlowTemplate', 'DestroyEntity',
                      'ShowAllHidedGroupInFlow', 'SetPlayerPos', 'SetPlotMode', 'PostAkEvent'}
    if include_suffix and any(not synchronous(action, action.get('Name'))
                              or action.get('Name') not in suffix_actions for action in actions[index + 1:]):
        return None
    projected = deepcopy(actions if include_suffix else actions[:index + 1])
    for item in projected[index]['Params']['TalkItems']:
        if item['Id'] == boundary.source_item['Id']:
            item.pop('Actions')
    parser = Exporter(source=source, allow_incomplete=True, speaker_records=names, choices=choices)
    parser.state_key = boundary.state_key
    try:
        if parser.actions(projected) or parser.missing:
            return None
    except (ValueError, KeyError, TypeError, IndexError):
        return None
    if include_suffix and any(len(group['visited_talk_ids']) != len(set(group['visited_talk_ids']))
                              for group in parser.talk_coverage):
        return None
    by_id = {item['Id']: item for item in items}
    for event in parser.events:
        if event.get('kind') == 'dialogue':
            event['source_item'] = deepcopy(by_id[event['talk_id']])
    return parser


def enrollment_fragment(actions, boundary, source, names, choices, prefix_count):
    """Inspect a conditional local continuation without claiming the UI returned."""
    from .rendering import render_result
    parser = _enrollment_parser(actions, boundary, source, names, choices)
    if parser is None:
        return None
    rendered = render_result({'title': '', 'route': {'choices': parser.decisions}, 'events': parser.events})
    return {'kind': 'unresolved_ui_continuation',
            'order_scope': 'configuration_after_unresolved_ui',
            'events': rendered['events'][prefix_count:], 'route': rendered['route'],
            'source_action': deepcopy(boundary.source_action),
            'runtime_return_verified': False, 'whole_segment_complete': False,
            'conditional_on_return_to_configured_dialogue': True}


def enrollment_return_route(actions, boundary, source, names, choices):
    """Place known text on the configured panel-return path, retaining the condition."""
    parser = _enrollment_parser(actions, boundary, source, names, choices, include_suffix=True)
    if parser is None:
        return None
    anchors = [i for i, event in enumerate(parser.events)
               if event.get('kind') == 'dialogue' and event.get('talk_id') == boundary.source_item['Id']]
    if len(anchors) != 1:
        return None
    anchor = anchors[0]
    parser.events.insert(anchor + 1, {
        'kind': 'ui_reference', 'state_key': boundary.state_key,
        'raw_text': '【入学界面】内部内容后置，以下按返回后的配置路径继续。',
        'source_action': deepcopy(boundary.source_action), 'content_deferred': True})
    parser.unverified_content.append({
        'kind': 'panel_return_text_route', 'source_action': deepcopy(boundary.source_action),
        'call_after_talk_id': boundary.source_item['Id'], 'call_after_event_index': anchor,
        'condition': 'panel_returns_to_configured_dialogue',
        'local_text_order_verified': True, 'runtime_return_verified': False,
        'panel_content_in_scope': False, 'panel_display_timing_verified': False,
        'conditional_on_panel_return': True, 'whole_task_complete': False,
        'original_boundary': boundary.as_dict(),
        'text_event_count': sum(event['kind'] in {'dialogue', 'choice'} for event in parser.events),
        'order_basis': 'original TalkItems order and selected explicit JumpTalk edges'})
    return parser


class PendingDialogueBoundary(ValueError):
    def __init__(self, kind, source_action, state_key, source_item):
        self.kind = kind
        self.source_action = deepcopy(source_action)
        self.state_key = state_key
        self.source_item = deepcopy(source_item)
        message = ('Conditional menu availability is unknown' if kind == 'conditional_menu'
                   else 'Combined item/option actions need ordering verification')
        super().__init__(message)

    def as_dict(self):
        return {'kind': self.kind + '_boundary', 'state_key': self.state_key,
                'action': self.source_action['Name'], 'source_action': self.source_action,
                'source_item': self.source_item,
                'boundary_executed': False, 'suffix_order_verified': False,
                'runtime_completion_verified': False, 'condition_values_evaluated': False,
                'options_selected': False}
