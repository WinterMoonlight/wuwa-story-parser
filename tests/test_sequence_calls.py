import unittest
from copy import deepcopy
from unittest.mock import patch
from wuwa_story.sequence_calls import sequence_call, head_icon
from wuwa_story.export_task import Exporter


class SequenceCallTests(unittest.TestCase):
    def test_sequence_shapes_and_unknown_callbacks_rejected(self):
        p = {'Path': '/Game/Test', 'ResetCamera': True, 'FrameEvents': [
            {'EventKey': 'A', 'EventActions': [{'Name': 'ChangeEntityState',
              'Params': {'Type': 'Directly', 'EntityId': 12, 'State': 'active'}}]}]}
        self.assertTrue(sequence_call(p))
        bad = deepcopy(p); bad['FrameEvents'][0]['EventActions'][0]['Name'] = 'PlayFlow'
        self.assertFalse(sequence_call(bad))
        bad = deepcopy(p); bad['ResetCamera'] = 1
        self.assertFalse(sequence_call(bad))
        bad = deepcopy(p); bad['FrameEvents'][0]['EventActions'][0]['Params']['EntityId'] = True
        self.assertFalse(sequence_call(bad))
        self.assertFalse(sequence_call({'Path': '', 'Extra': True}))

    def test_sequence_marker_preserves_callbacks_without_executing(self):
        p = Exporter(allow_incomplete=True); p.state_key = 'test'
        action = {'Name': 'PlaySequenceData', 'Params': {'Path': '/Game/Test', 'ResetCamera': True}}
        p.action(action)
        self.assertEqual(p.events[0]['kind'], 'unparsed_content')
        self.assertEqual(p.events[0]['source_action'], action)
        self.assertFalse(p.unverified_content[0]['frame_events_executed'])
        strict = Exporter(); strict.state_key = 'test'
        with self.assertRaises(ValueError): strict.action(action)

    def test_combined_icon_does_not_change_speaker_or_choice(self):
        icon = {'Name': 'SetHeadIconVisible', 'Params': {
            'HeadStyleConfig': {'Type': 0, 'WhoId': 1007}, 'Visible': True}}
        item = {'Id': 1, 'Type': 'Talk', 'WhoId': 108, 'TidTalk': 'hello',
                'Actions': [icon], 'Options': [{'TidTalkOption': 'yes'}]}
        p = Exporter(allow_incomplete=True); p.state_key = 'test'
        with patch('wuwa_story.export_task.texts', {'hello': '你好', 'yes': '好的'}): p.talk([item])
        self.assertEqual(p.events[0]['speaker_id'], 108)
        self.assertEqual(p.events[1]['kind'], 'choice')
        self.assertEqual(p.decisions[0]['selected_index'], 0)
        bad = deepcopy(icon['Params']); bad['Visible'] = 1
        self.assertFalse(head_icon(bad))
