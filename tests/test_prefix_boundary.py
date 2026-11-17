import copy
import unittest
from wuwa_story.prefix_boundary import UnresolvedControlBoundary, unresolved_control_shape


def assignment():
    return {'Name': 'SetVar', 'Params': {
        'VarLeft': {'Type': 'Boolean', 'Source': 'Self', 'Name': 'continue'},
        'VarRight': {'Type': 'Boolean', 'Source': 'Constant', 'Value': True}}}


class PrefixBoundaryTests(unittest.TestCase):
    def test_only_exact_synchronous_controls(self):
        finish = {'Name': 'FinishState', 'Params': {}}
        for action in (finish, assignment()):
            self.assertTrue(unresolved_control_shape(action))
            self.assertTrue(unresolved_control_shape(dict(action, Async=False, ActionId=1)))
            for extra in ({'Async': True}, {'Async': 0}, {'Timeout': 1}, {'OnFinish': []}):
                self.assertFalse(unresolved_control_shape(dict(action, **extra)))
        for action in (None, [], {}, {'Name': 'FinishState'},
                       {'Name': 'FinishState', 'Params': None},
                       {'Name': 'FinishState', 'Params': {'StateId': 2}},
                       {'Name': 'ChangeState', 'Params': {'StateId': 2}}):
            self.assertFalse(unresolved_control_shape(action))

    def test_no_global_or_unknown_write_shape(self):
        a = assignment(); a['Params']['VarLeft']['Source'] = 'Global'
        self.assertFalse(unresolved_control_shape(a))
        a = assignment(); a['Params']['VarRight']['Source'] = 'Self'
        self.assertFalse(unresolved_control_shape(a))
        a = assignment(); a['Params']['VarRight']['Value'] = 1
        self.assertFalse(unresolved_control_shape(a))
        a = assignment(); a['Params']['VarLeft']['Type'] = 'Int'
        self.assertFalse(unresolved_control_shape(a))

    def test_exception_preserves_source_and_original_error_text(self):
        action = assignment(); original = copy.deepcopy(action)
        exc = UnresolvedControlBoundary(action, 'flow_1_1')
        self.assertIsInstance(exc, ValueError)
        self.assertEqual(str(exc), 'Unsupported action: SetVar')
        action['Params']['VarRight']['Value'] = False
        self.assertEqual(exc.source_action, original)
        record = exc.as_dict()
        self.assertEqual(record['state_key'], 'flow_1_1')
        self.assertFalse(record['boundary_executed'])
        self.assertFalse(record['suffix_order_verified'])
        self.assertFalse(record['runtime_completion_verified'])
        record['source_action']['Params']['VarRight']['Value'] = False
        self.assertEqual(exc.source_action, original)
        with self.assertRaisesRegex(ValueError, 'boundary shape'):
            UnresolvedControlBoundary({'Name': 'Unknown', 'Params': {}})
