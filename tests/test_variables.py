import copy
import unittest

from wuwa_story.variables import VariableEnvironment, set_var_shape, compare_var_shape


def reference(source='Self'):
    return {'Type': 'Boolean', 'Source': source, 'Name': 'right_path'}


def assignment(value, source='Self'):
    return {'Name': 'SetVar', 'Params': {'VarLeft': reference(source),
            'VarRight': {'Type': 'Boolean', 'Source': 'Constant', 'Value': value}}}


def condition(value, source='Self'):
    return {'Type': 'CompareVar', 'Var1': reference(source), 'Compare': 'Eq',
            'Var2': {'Type': 'Boolean', 'Source': 'Constant', 'Value': value}}


class VariableTests(unittest.TestCase):
    def test_unknown_is_not_false_and_choices_match_conditions(self):
        env = VariableEnvironment('quest:A')
        self.assertIsNone(env.evaluate(condition(False)))
        self.assertIsNone(env.evaluate(condition(True)))
        for choice in (False, True):
            branch = env.fork(); record = branch.assign(assignment(choice))
            self.assertFalse(record['before_known'])
            self.assertIs(branch.evaluate(condition(choice)), True)
            self.assertIs(branch.evaluate(condition(not choice)), False)
        self.assertIsNone(env.read(reference()))

    def test_scopes_and_failed_branch_are_isolated(self):
        a = VariableEnvironment('quest:A', 'world:A'); b = VariableEnvironment('quest:B', 'world:A')
        a.assign(assignment(True))
        self.assertIsNone(a.read(reference('Global')))
        self.assertIsNone(b.read(reference()))
        branch = a.fork(); branch.assign(assignment(False))
        self.assertIs(a.read(reference()), True)
        branch.assign(assignment(True, 'Global'))
        self.assertIsNone(a.read(reference('Global')))
        with self.assertRaises(ValueError): VariableEnvironment('quest:A').assign(assignment(True, 'Global'))

    def test_trace_keeps_order_and_does_not_alias_inputs(self):
        env = VariableEnvironment('quest:A'); action = assignment(False)
        result = env.assign(action, {'talk_id': 1})
        result['after'] = True; action['Params']['VarRight']['Value'] = True
        self.assertIs(env.read(reference()), False)
        record = env.assign(assignment(True))
        self.assertTrue(record['before_known']); self.assertIs(record['before'], False)
        self.assertEqual([r['after'] for r in env.trace], [False, True])
        self.assertEqual(env.snapshot()[0]['scope_id'], 'quest:A')

    def test_exact_shapes_reject_unproved_operations(self):
        self.assertTrue(set_var_shape(assignment(False)))
        self.assertTrue(compare_var_shape(condition(False)))
        for action in [assignment(0), assignment(None), dict(assignment(True), Async=True),
                       dict(assignment(True), Callbacks=[])]:
            self.assertFalse(set_var_shape(action))
        action = assignment(True); action['Params']['VarRight'] = reference()
        self.assertFalse(set_var_shape(action))
        for key, value in [('Compare', 'Ne'), ('Extra', [])]:
            bad = dict(condition(True)); bad[key] = value
            self.assertFalse(compare_var_shape(bad))
        bad = copy.deepcopy(condition(True)); bad['Var1']['Type'] = 'Int'
        self.assertFalse(compare_var_shape(bad))
        with self.assertRaises(ValueError): VariableEnvironment('quest:A').evaluate(bad)


if __name__ == '__main__':
    unittest.main()
