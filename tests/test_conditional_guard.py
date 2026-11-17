import copy
import unittest
from wuwa_story.conditional_guard import conditional_variable_guard

REF = {'Type': 'Boolean', 'Source': 'Self', 'Name': 'side'}
def assign(name='side'):
    return {'Name': 'SetVar', 'Params': {'VarLeft': dict(REF, Name=name),
            'VarRight': {'Type': 'Boolean', 'Source': 'Constant', 'Value': True}}}

class ConditionalGuardTests(unittest.TestCase):
    def setUp(self):
        self.writer = {'Id': 2, 'ParentNodeId': 1, 'FinishActions': []}
        self.selector = {'Id': 4, 'ParentNodeId': 1}
        self.parent = {'Id': 1, 'Type': 'Sequence'}
    def guard(self, actions=None, extra=None):
        return conditional_variable_guard(actions or [], self.writer, self.selector,
            [self.parent, self.writer, self.selector] + (extra or []), REF)
    def test_no_order_is_not_runtime_proof(self):
        result = self.guard()
        self.assertTrue(result['allowed'])
        self.assertEqual(result['parent_order_evidence'], 'not_available')
        self.assertFalse(result['runtime_order_verified'])
        self.assertFalse(result['external_writers_verified_absent'])
    def test_known_writer_finish_and_selector_enter_overwrites_rejected(self):
        for target, field in ((self.writer, 'FinishActions'), (self.selector, 'EnterActions')):
            target[field] = [assign()]
            result = self.guard()
            self.assertFalse(result['allowed'])
            self.assertEqual(result['reasons'][0]['code'], 'possible_variable_overwrite')
            target[field] = []
        self.writer['FinishActions'] = [assign('unrelated')]
        self.assertTrue(self.guard()['allowed'])
    def test_async_ancestor_of_assignment_rejected(self):
        actions = [{'Name': 'ShowTalk', 'Async': True, 'Params': {'TalkItems': [
            {'Options': [{'Actions': [assign()]}]}]}}]
        self.assertFalse(self.guard(actions)['allowed'])
        actions[0]['Async'] = False
        self.assertTrue(self.guard(actions)['allowed'])
    def test_explicit_intermediate_writes_and_reversed_order(self):
        self.parent['Children'] = [2, 3, 4]
        middle = {'Id': 3, 'FinishActions': [assign()]}
        self.assertFalse(self.guard(extra=[middle])['allowed'])
        middle['FinishActions'] = [assign('unrelated')]
        self.assertTrue(self.guard(extra=[middle])['allowed'])
        self.assertFalse(self.guard()['allowed'])
        self.parent['Children'] = [4, 2]
        self.assertEqual(self.guard()['reasons'][0]['code'], 'parent_order_contradicts_recap')
    def test_unknown_write_target_and_state_control_do_not_pass(self):
        self.writer['FinishActions'] = [{'Name': 'SetVar', 'Params': {}}]
        self.assertFalse(self.guard()['allowed'])
        self.selector['EnterActions'] = [{'Name': 'ChangeState', 'Params': {'StateId': 2}}]
        self.writer['FinishActions'] = []
        self.assertFalse(self.guard()['allowed'])
    def test_malformed_assignment_params_are_rejections_not_exceptions(self):
        for params in (None, [], 'unknown', 7):
            self.writer['FinishActions'] = [{'Name': 'SetVar', 'Params': params}]
            result = self.guard()
            self.assertFalse(result['allowed'])
            self.assertEqual(result['reasons'][0]['code'], 'possible_variable_overwrite')

    def test_embedded_children_are_inspected_without_mutation(self):
        self.parent['Children'] = [self.writer, {'Id': 3, 'EnterActions': [assign()]}, self.selector]
        original = copy.deepcopy(self.parent)
        self.assertFalse(self.guard()['allowed'])
        self.assertEqual(self.parent, original)

if __name__ == '__main__': unittest.main()
