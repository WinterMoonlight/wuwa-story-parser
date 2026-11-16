import unittest
from wuwa_story.branch_recap import annotate_branch_entries


class BranchRecapTests(unittest.TestCase):
    def fixture(self):
        flow = {'FlowListName': 'f', 'FlowId': 1, 'StateId': 2}
        leaf = {'Id': 3, 'Type': 'ChildQuest', 'TidTip': 'left',
                'FinishActions': [{'Name': 'PlayFlow', 'Params': flow}]}
        selector = {'Id': 1, 'Type': 'ConditionSelector', 'Slots': [
            {'Condition': {'Type': 0}, 'Node': leaf}]}
        return flow, leaf, selector

    def test_exact_flow_and_occurrence(self):
        f, leaf, selector = self.fixture()
        entries = [{'TidTip': 'left'}, {'Flow': f},
                   {'Flow': dict(f, StateId=9)}, {'TidTip': 'other'}, {'Flow': f}]
        got = annotate_branch_entries(entries, [selector, leaf])
        self.assertEqual(set(got), {0, 1})
        self.assertEqual(got[1]['slot_index'], 0)

    def test_ambiguous_tip_or_membership_is_unresolved(self):
        f, leaf, selector = self.fixture()
        entries = [{'TidTip': 'left'}, {'Flow': f}]
        other = dict(leaf, Id=4)
        self.assertEqual(annotate_branch_entries(entries, [selector, leaf, other]), {})
        selector['Slots'].append(selector['Slots'][0])
        self.assertEqual(annotate_branch_entries(entries, [selector, leaf]), {})

    def test_unanchored_matching_flow_is_not_assigned(self):
        f, leaf, selector = self.fixture()
        self.assertEqual(annotate_branch_entries([{'Flow': f}], [selector, leaf]), {})
