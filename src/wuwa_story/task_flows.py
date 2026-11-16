"""Classify flow occurrences from their callers, never from flow names."""
from collections import defaultdict
import math
from .export_task import flow_key
from .external import node_context


def validate_bubble(params):
    required = {'EntityIds', 'EnterRadius', 'LeaveRadius', 'Flow'}
    if not required <= params.keys() or params.keys() - required - {'WaitTime'}:
        raise ValueError('Unsupported bubble parameters')
    if not isinstance(params['EntityIds'], list) or not params['EntityIds'] or any(type(x) is not int for x in params['EntityIds']):
        raise ValueError('Unsupported bubble entities')
    for key in ('EnterRadius', 'LeaveRadius', 'WaitTime'):
        v = params.get(key, 0)
        if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
            raise ValueError('Unsupported bubble distance/time')
    if params['LeaveRadius'] < params['EnterRadius']:
        raise ValueError('Unsupported bubble distance order')
    flow = params['Flow']
    if not isinstance(flow, dict) or set(flow) != {'FlowListName', 'FlowId', 'StateId'} or not flow['FlowListName']:
        raise ValueError('Unsupported bubble flow')


def classify_task_flows(quest, nodes):
    result = defaultdict(list)
    def visit(value, path, context, action=None):
        if isinstance(value, dict):
            if 'Name' in value and 'Params' in value:
                action = value
            if value.get('FlowListName') and 'FlowId' in value and 'StateId' in value:
                kind = 'unverified'
                if context.get('route_scope') == 'failure_branch':
                    kind = 'failure_branch'
                elif action and action.get('Name') == 'AddPlayBubble' and action.get('Params', {}).get('Flow') is value:
                    try:
                        validate_bubble(action['Params'])
                        kind = 'proximity_bubble'
                    except ValueError:
                        pass
                elif action and action.get('Name') == 'PlayFlow':
                    kind = 'task_action'
                elif 'Condition' in path:
                    kind = 'task_condition'
                result[flow_key(value)].append({'kind': kind, 'path': path, 'context': context,
                                                'caller': action, 'runtime_verified': False})
            for key, child in value.items():
                visit(child, path + [key], context, action)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                visit(child, path + [i], context, action)
    visit(quest, ['quest'], {})
    for node in nodes:
        visit(node, ['nodes', node['Id']], node_context(node, nodes))
    return dict(result)


def bubble_only_extras(references, ordered, occurrences):
    return {key for key in references - set(ordered) if occurrences.get(key) and
            all(o['kind'] == 'proximity_bubble' for o in occurrences[key])}


def inspect_bubble(params, read_rows):
    import hashlib
    from types import SimpleNamespace
    from .export_task import Exporter, flow_actions
    from .rendering import render_text
    validate_bubble(params)
    key = flow_key(params['Flow'])
    matches = [r for r in read_rows('db_flowState.db', 'flowstate') if r['StateKey'] == key]
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous bubble flow')
    parser = Exporter(source=SimpleNamespace(rows=read_rows), allow_incomplete=True)
    parser.state_key = key
    actions, fields = flow_actions(matches[0]['BinData'])
    if parser.actions(actions):
        raise ValueError('Unexpected bubble flow control')
    return {'state_key': key, 'source_actions': actions, 'action_fields': fields,
            'sha256': hashlib.sha256(matches[0]['BinData']).hexdigest(),
            'trigger_config': params, 'local_order_verified': True, 'runtime_verified': False,
            'unverified_content': parser.unverified_content, 'missing_text_ids': parser.missing,
            'texts': [{'text_id': e.get('text_id'), 'raw_text': e['raw_text'],
                       'display_name': render_text(e.get('display_name', '旁白')),
                       'missing': e.get('text_id') in parser.missing, 'source_event': e}
                      for e in parser.events]}
