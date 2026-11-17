"""Choose only explicit unconditional menu entries, without evaluating guards."""
from copy import deepcopy


def _guard_shape(guard):
    if not isinstance(guard, dict) or set(guard) != {'Type', 'Conditions'} or guard['Type'] != 'Condition':
        return False
    group = guard['Conditions']
    if (not isinstance(group, dict) or set(group) != {'Type', 'Conditions'}
            or type(group['Type']) is not int or group['Type'] not in (0, 1)
            or not isinstance(group['Conditions'], list) or not group['Conditions']):
        return False
    for c in group['Conditions']:
        if not isinstance(c, dict):
            return False
        if c.get('Type') == 'CompareVar':
            from .variables import compare_var_shape
            if not compare_var_shape(c) or c['Var1']['Source'] != 'Self':
                return False
        elif c.get('Type') == 'CheckItems':
            if (set(c) != {'Type', 'Compare', 'Items'} or c['Compare'] != 'Ge'
                    or not isinstance(c['Items'], list) or not c['Items']):
                return False
            for item in c['Items']:
                if (not isinstance(item, dict) or set(item) != {'ItemId', 'Count'}
                        or any(type(item[k]) is not int or item[k] <= 0 for k in item)):
                    return False
        else:
            return False
    return True


def candidate_indices(options):
    """Original indices only; guarded entries are unknown, never called false."""
    if not isinstance(options, list):
        raise ValueError('Invalid menu options')
    allowed = []
    for i, option in enumerate(options):
        if not isinstance(option, dict):
            raise ValueError('Invalid menu option')
        if any('condition' in k.lower() and k != 'PreCondition' for k in option):
            raise ValueError('Unsupported option condition field')
        if 'PreCondition' in option:
            if not _guard_shape(option['PreCondition']):
                raise ValueError('Unsupported option guard shape')
        else:
            allowed.append(i)
    return allowed


def select_option(options, override=None, tried=None):
    allowed = candidate_indices(options)
    tried = set() if tried is None else set(tried)
    if override is not None:
        if type(override) is not int or override not in allowed:
            raise ValueError('Selected option has unknown availability or invalid index')
        if override in tried:
            raise ValueError('Selected option was already tried')
        return override
    remaining = [i for i in allowed if i not in tried]
    if not remaining:
        raise ValueError('No untried unconditional option')
    return remaining[0]


def selection_evidence(options):
    allowed = candidate_indices(options)
    excluded = [i for i in range(len(options)) if i not in allowed]
    return {'kind': 'unconditional_option_selection', 'eligible_original_indices': allowed,
            'excluded_original_indices': excluded,
            'source_conditions': [{'original_index': i, 'condition': deepcopy(options[i]['PreCondition'])}
                                  for i in excluded],
            'condition_values_evaluated': False, 'guarded_option_visibility_verified': False,
            'policy': 'first_untried_unconditional_unless_explicit_unconditional_override'}


def preflight_walk(value):
    """Skip only recognized guards directly on Options entries during preflight.

    Actions and every other subtree are still yielded. The source is untouched;
    yielded option dictionaries omit PreCondition solely for the legacy generic
    condition detector, never for actual menu selection or source evidence.
    """
    if isinstance(value, dict):
        yield value
        for key, child in value.items():
            if key == 'Options':
                candidate_indices(child)
                for option in child:
                    projected = {k: v for k, v in option.items() if k != 'PreCondition'}
                    yield from preflight_walk(projected)
            else:
                yield from preflight_walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from preflight_walk(child)


def write_audit_projection(value):
    """Copy for write-only audit, never execution; guarded options stay unselected."""
    if isinstance(value, list):
        return [write_audit_projection(v) for v in value]
    if not isinstance(value, dict):
        return deepcopy(value)
    result = {}
    for key, child in value.items():
        if key == 'Options':
            candidate_indices(child)
            result[key] = [write_audit_projection({k:v for k,v in o.items() if k != 'PreCondition'}) for o in child]
        else:
            result[key] = write_audit_projection(child)
    return result
