"""Audit constant writes on a selected local path, without a runtime environment.

These records cannot be read or evaluated as game variables. In particular,
Global/Keyword identifiers do not establish a shared world-state scope.
"""
from copy import deepcopy
from .database import texts
from .rendering import render_text


def constant_write_shape(action):
    if (not isinstance(action, dict) or action.get('Name') != 'SetVar'
            or set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            or action.get('Async', False) is not False):
        return False
    params = action.get('Params')
    if not isinstance(params, dict) or set(params) != {'VarLeft', 'VarRight'}:
        return False
    left, right = params['VarLeft'], params['VarRight']
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    if left.get('Source') == 'Self':
        name_key = 'Name'
    elif left.get('Source') == 'Global':
        name_key = 'Keyword'
    else:
        return False
    if (set(left) != {'Type', 'Source', name_key}
            or not isinstance(left[name_key], str) or not left[name_key].strip()
            or set(right) != {'Type', 'Source', 'Value'}
            or right['Source'] != 'Constant' or left['Type'] != right['Type']):
        return False
    kind, value = left['Type'], right['Value']
    return ((kind == 'Boolean' and type(value) is bool)
            or (kind == 'Int' and type(value) is int and -(2**31) <= value < 2**31)
            or (kind == 'String' and type(value) is str))


class ConstantWriteRecorder:
    """Append-only audit of reached assignments; deliberately no read/evaluate."""
    record_only = True

    def __init__(self, scope):
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError('A local audit scope is required')
        self.self_scope = scope
        self.trace = []

    def assign(self, action, evidence=None):
        if not constant_write_shape(action):
            raise ValueError('Unsupported constant write audit')
        params = action['Params']
        record = {'kind': 'selected_route_constant_write', 'scope_id': self.self_scope,
                  'variable': deepcopy(params['VarLeft']),
                  'recorded_constant': deepcopy(params['VarRight']['Value']),
                  'source_action': deepcopy(action), 'runtime_executed': False,
                  'previous_value_known': False, 'global_state_established': False,
                  'downstream_effects_verified': False}
        if evidence is not None:
            record['evidence'] = deepcopy(evidence)
        self.trace.append(record)
        return deepcopy(record)

    def snapshot(self):
        """Return recorded assignments, not a map of actual variable values."""
        return [{'variable': deepcopy(r['variable']),
                 'recorded_constant': deepcopy(r['recorded_constant']),
                 'runtime_executed': False} for r in self.trace]


def constant_write_recorder(actions, scope):
    """Accept a whole write-only tree; reject conditions, reads and transfers."""
    writes = []

    def check(value):
        if isinstance(value, list):
            return all(check(v) for v in value)
        if not isinstance(value, dict):
            return True
        if value.get('Name') == 'SetVar':
            if not constant_write_shape(value):
                return False
            writes.append(value)
            return True
        if value.get('Name') in ('FinishState', 'ChangeState', 'PlayFlow'):
            return False
        if any('condition' in k.lower() or 'var' in k.lower() for k in value):
            return False
        if value.get('Source') in ('Self', 'Global', 'Keyword'):
            return False
        for key, text_key in value.items():
            if isinstance(text_key, str) and (key.startswith('Tid') or key == 'PlotLineKey'):
                raw = texts.get(text_key)
                if raw is not None:
                    rendered = render_text(raw)
                    # Known Rover templates are fixed by the reading policy.
                    # Any remaining format placeholder might read runtime state.
                    if any(char in rendered for char in '{}%'):
                        return False
        return all(check(v) for v in value.values())

    if not check(actions) or not writes:
        return None
    return ConstantWriteRecorder(scope)
