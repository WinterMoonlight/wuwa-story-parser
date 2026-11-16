"""A small, explicitly scoped Boolean environment for selected config routes.

This module does not choose a route, infer an initial value, or carry state across
unrelated recap entries. Callers provide scope identities and commit only the
environment belonging to the selected, successfully parsed path.
"""
from copy import deepcopy


def _reference(value):
    return (isinstance(value, dict)
            and set(value) == {'Type', 'Source', 'Name'}
            and value['Type'] == 'Boolean'
            and value['Source'] in ('Self', 'Global')
            and isinstance(value['Name'], str) and bool(value['Name'].strip()))


def _constant(value):
    return (isinstance(value, dict)
            and set(value) == {'Type', 'Source', 'Value'}
            and value['Type'] == 'Boolean' and value['Source'] == 'Constant'
            and type(value['Value']) is bool)


def set_var_shape(action):
    if (not isinstance(action, dict) or action.get('Name') != 'SetVar'
            or set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            or action.get('Async', False) is not False):
        return False
    params = action.get('Params')
    return (isinstance(params, dict) and set(params) == {'VarLeft', 'VarRight'}
            and _reference(params['VarLeft']) and _constant(params['VarRight']))


def compare_var_shape(condition):
    return (isinstance(condition, dict)
            and set(condition) == {'Type', 'Var1', 'Compare', 'Var2'}
            and condition['Type'] == 'CompareVar' and condition['Compare'] == 'Eq'
            and _reference(condition['Var1']) and _constant(condition['Var2']))


class VariableEnvironment:
    def __init__(self, self_scope, global_scope=None):
        if not isinstance(self_scope, str) or not self_scope.strip():
            raise ValueError('An explicit Self scope identity is required')
        if global_scope is not None and (not isinstance(global_scope, str) or not global_scope.strip()):
            raise ValueError('Global scope identity must be explicit or absent')
        self.self_scope = self_scope
        self.global_scope = global_scope
        self._values = {}
        self.trace = []

    def _key(self, reference):
        if not _reference(reference):
            raise ValueError('Unsupported variable reference')
        scope = self.self_scope if reference['Source'] == 'Self' else self.global_scope
        if scope is None:
            raise ValueError('Global variable scope has not been established')
        return reference['Source'], scope, reference['Type'], reference['Name']

    def read(self, reference):
        """Return a Boolean or None for an unassigned variable, never false by default."""
        return self._values.get(self._key(reference))

    def assign(self, action, evidence=None):
        if not set_var_shape(action):
            raise ValueError('Unsupported constant Boolean assignment')
        params = action['Params']; reference = params['VarLeft']
        key = self._key(reference)
        before = self._values.get(key)
        value = params['VarRight']['Value']
        self._values[key] = value
        record = {'kind': 'selected_route_variable_assignment',
                  'variable': deepcopy(reference), 'scope_id': key[1],
                  'before_known': before is not None, 'before': before,
                  'after': value, 'source_action': deepcopy(action)}
        if evidence is not None:
            record['evidence'] = deepcopy(evidence)
        self.trace.append(record)
        return deepcopy(record)

    def evaluate(self, condition):
        """Return True/False/None; None means no established value for this scope."""
        if not compare_var_shape(condition):
            raise ValueError('Unsupported Boolean equality condition')
        value = self.read(condition['Var1'])
        return None if value is None else value == condition['Var2']['Value']

    def fork(self):
        """Make an isolated branch/transaction. Caller explicitly chooses which to keep."""
        return deepcopy(self)

    def snapshot(self):
        return [{'source': source, 'scope_id': scope, 'type': kind, 'name': name, 'value': value}
                for (source, scope, kind, name), value in sorted(self._values.items())]
