"""Audit prerequisites for a Reigns solver; never replace unknown buffs by zero."""
from .export_task import walk


def compare(value, operation, target):
    if value is None:
        return None
    operations = {'Eq': lambda: value == target, 'Ne': lambda: value != target,
                  'Ge': lambda: value >= target, 'Gt': lambda: value > target,
                  'Le': lambda: value <= target, 'Lt': lambda: value < target}
    if operation not in operations:
        raise ValueError('Unknown Reigns comparison: ' + operation)
    return operations[operation]()


def audit_rules(actions, endings, initial_properties):
    calls = [a for a in walk(actions) if 'Name' in a and 'Params' in a]
    buffs = sorted({a['Params']['BuffId'] for a in calls if a['Name'] == 'ReignsAddBuff'})
    properties = {p['Id']: p['BaseValue'] for p in initial_properties}
    probes = []
    for index, ending in enumerate(endings):
        condition = ending['Conditions']
        terms = condition['Conditions']
        initial = [compare(properties.get(t['PropertyId']), t['Compare'], t['Target']) for t in terms]
        probes.append({'ending_index': index, 'is_success': ending['IsSuccess'],
                       'condition_type_raw': condition['ConditionType'], 'terms': terms,
                       'initial_term_results': initial,
                       'initial_if_all': all(initial) if None not in initial else None,
                       'initial_if_any': any(initial) if None not in initial else None,
                       'card_id': ending.get('CardId'), 'card_ids': ending.get('CardIds', []),
                       'card_field_precedence_verified': False})
    return {'buff_ids': buffs, 'buff_effects_resolved': 0,
            'settlement_calls': [a for a in calls if a['Name'] == 'ReignsCheckSettle'],
            'ending_probes': probes, 'probe_scope': 'Initial values only, not a played route',
            'route_attempt': {'status': 'blocked_missing_semantics', 'successful_route': None,
                'blockers': ['No verified Reigns BuffId-to-property effect definitions in supplied configuration',
                             'ConditionType 0/1 combination mapping is not verified',
                             'Buff application timing, stacking, clamping and settlement timing are not verified',
                             'CardId/CardIds precedence and simultaneous-ending priority are not verified']}}
