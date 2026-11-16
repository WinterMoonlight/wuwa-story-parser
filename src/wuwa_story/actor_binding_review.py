"""Keep explicit dialogue readable when a cinematic actor table is absent.

This does not resolve an actor or infer an anonymous speaker's identity.
"""


def unbound_change_readable(action, actors, talk_items):
    if actors != [] or not isinstance(talk_items, list) or not talk_items:
        return False
    if (not isinstance(action, dict) or action.get('Name') != 'ChangeActorTalker'
            or set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            or action.get('Async', False) is not False):
        return False
    params = action.get('Params')
    if not isinstance(params, dict) or set(params) != {'ActorIndex', 'Talker'}:
        return False
    if any(type(params[k]) is not int or params[k] < 0 for k in params):
        return False
    # Validate the entire active ShowTalk, including backward JumpTalk targets.
    # Do not continue on an implicit actor-based speaker, QTE, or control item.
    return all(isinstance(item, dict) and item.get('Type') == 'Talk'
               and type(item.get('WhoId')) is int and item['WhoId'] >= 0
               for item in talk_items)


def unbound_change_evidence(action):
    return {
        'kind': 'unbound_actor_change',
        'source_action': action,
        'binding_resolved': False,
        'identity_inferred': False,
        'callbacks_verified': False,
        'note': 'Actor table absent; keep explicit subsequent WhoId and source order; '
                'do not create a binding or rewrite anonymous speakers',
    }
