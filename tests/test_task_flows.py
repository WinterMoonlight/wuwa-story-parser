import unittest
from copy import deepcopy
from wuwa_story.task_flows import classify_task_flows, bubble_only_extras, validate_bubble
from wuwa_story.export_task import Exporter
from wuwa_story.coverage import validate_world_effect
from wuwa_story.reading import reading_text


class TaskFlowsTests(unittest.TestCase):
    def setUp(self):
        self.flow = {'FlowListName': 'test', 'FlowId': 1, 'StateId': 1}
        self.params = {'EntityIds': [1], 'EnterRadius': 500, 'LeaveRadius': 1500, 'Flow': self.flow}
        self.node = {'Id': 1, 'ParentNodeId': 0, 'Type': 'ChildQuest',
                     'FinishActions': [{'Name': 'AddPlayBubble', 'Params': self.params}]}

    def test_shared_normal_reference_cannot_be_removed(self):
        node = deepcopy(self.node)
        node['FinishActions'].append({'Name': 'PlayFlow', 'Params': self.flow})
        refs = classify_task_flows({}, [node])
        self.assertEqual(bubble_only_extras({'test_1_1'}, [], refs), set())

    def test_bubble_failure_and_condition_are_distinct(self):
        refs = classify_task_flows({}, [self.node])
        self.assertEqual(bubble_only_extras({'test_1_1'}, [], refs), {'test_1_1'})
        node = deepcopy(self.node);node['Type'] = 'QuestFailed'
        refs = classify_task_flows({}, [node])
        self.assertEqual(refs['test_1_1'][0]['kind'], 'failure_branch')
        self.assertFalse(bubble_only_extras({'test_1_1'}, [], refs))
        node = {'Id': 1, 'Type': 'ChildQuest', 'ParentNodeId': 0,
                'Condition': {'Type': 'DoInteract', 'Flow': self.flow}}
        self.assertEqual(classify_task_flows({}, [node])['test_1_1'][0]['kind'], 'task_condition')

    def test_unknown_bubble_payload_rejected(self):
        with self.assertRaises(ValueError):validate_bubble({**self.params, 'UnknownFlag': True})
        with self.assertRaises(ValueError):validate_bubble({**self.params, 'EnterRadius': -1})

    def test_real_task_retains_bubbles_and_unknown_content(self):
        r = Exporter(allow_incomplete=True).export(139000027)
        self.assertEqual(len(r['events']), 430)
        bubbles = [e for e in r['external_content'] if 'bubble' in e]
        self.assertEqual([len(e['texts']) for e in bubbles], [9, 20])
        self.assertEqual(len(r['source']['recap_reference_resolution']['separate_bubble_references']), 2)
        self.assertEqual(r['validation']['status'], 'needs_review')
        self.assertFalse(r['validation']['complete_for_supported_task_shape'])
        self.assertEqual(len([e for e in r['external_content'] if 'source_path' in e]), 5)
        text = reading_text(r)
        for e in bubbles:
            self.assertTrue(all(t['text'] in text for t in e['texts']))
        self.assertNotIn('WaitTime', text)
        self.assertTrue(any(x['kind'] == 'unparsed_flow_content' for x in r['validation']['unverified_content']))
        with self.assertRaises(ValueError):Exporter().export(139000027)

    def test_module_restrictions_do_not_accept_unknown_fields(self):
        params = {'Type': 'DisableModule', 'MoveOption': {'Type': 'Disable', 'Forward': True},
                  'SkillOption': {'Type': 'Disable', 'DisplayMode': 'Hide'},
                  'UiOption': {'Type': 'EnableSectionalUi', 'ShowQuestTrack': True}}
        validate_world_effect('SetPlayerOperationRestriction', params)
        with self.assertRaises(ValueError):
            validate_world_effect('SetPlayerOperationRestriction', {**params, 'Other': True})


if __name__ == '__main__': unittest.main()
