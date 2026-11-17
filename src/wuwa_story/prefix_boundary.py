"""Explicit unresolved controls at which a recap may retain an ordered prefix.

Recognition does not execute a control or define its runtime semantics. Callers
must keep the containing segment blocked and append its original gap marker.
"""
from copy import deepcopy
from .variables import set_var_shape


def unresolved_control_shape(action):
    """Only observed synchronous local Boolean writes or an empty FinishState."""
    if not isinstance(action, dict):
        return False
    if action.get('Name') == 'SetVar':
        return (set_var_shape(action)
                and action['Params']['VarLeft']['Source'] == 'Self')
    return (action.get('Name') == 'FinishState'
            and {'Name', 'Params'} <= set(action)
            and set(action) <= {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            and action.get('Async', False) is False
            and action['Params'] == {})


class UnresolvedControlBoundary(ValueError):
    """A reached, unexecuted control; unlike arbitrary parse/validation errors."""

    def __init__(self, action, state_key=None):
        if not unresolved_control_shape(action):
            raise ValueError('Unsupported unresolved-control boundary shape')
        self.source_action = deepcopy(action)
        self.state_key = state_key
        super().__init__('Unsupported action: ' + action['Name'])

    def as_dict(self):
        return {'kind': 'unresolved_control_boundary',
                'state_key': self.state_key,
                'action': self.source_action['Name'],
                'source_action': deepcopy(self.source_action),
                'boundary_executed': False,
                'suffix_order_verified': False,
                'runtime_completion_verified': False}
