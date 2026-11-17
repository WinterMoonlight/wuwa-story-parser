"""Local constant writes can be recorded without guessing an initial value."""
from .variables import set_var_shape, VariableEnvironment


def write_only_environment(actions, scope):
    writes = []
    def check(value):
        if isinstance(value, list):
            return all(check(v) for v in value)
        if not isinstance(value, dict):
            return True
        if value.get('Name') == 'SetVar':
            if not set_var_shape(value) or value['Params']['VarLeft']['Source'] != 'Self':
                return False
            writes.append(value)
            return True
        if value.get('Name') in ('FinishState', 'ChangeState', 'PlayFlow'):
            return False
        if any('condition' in k.lower() or 'var' in k.lower() for k in value):
            return False
        if value.get('Source') in ('Self', 'Global', 'Keyword'):
            return False
        return all(check(v) for v in value.values())
    if not check(actions) or not writes:
        return None
    return VariableEnvironment(scope)
