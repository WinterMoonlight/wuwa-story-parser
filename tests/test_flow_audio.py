import unittest
from unittest.mock import patch
from wuwa_story.export_task import Exporter
from wuwa_story.reading_effects import flow_audio_state_shape


class FlowAudioTests(unittest.TestCase):
    def test_audio_state_preserves_speech_and_choice_order(self):
        p = Exporter(allow_incomplete=True); p.state_key = 'test'
        a = {'Name': 'SetAudioState', 'Params': {'AudioConfig': {'Group': 'g', 'State': 'before'}}}
        b = {'Name': 'SetAudioState', 'Params': {'AudioConfig': {'Group': 'g', 'State': 'after'}}}
        with patch('wuwa_story.export_task.texts', {'a': '对白', 'b': '选择', 'c': '后续'}):
            p.actions([a, {'Name': 'ShowTalk', 'Params': {'TalkItems': [
                {'Id': 1, 'Type': 'Talk', 'TidTalk': 'a', 'Options': [{'TidTalkOption': 'b'}]},
                {'Id': 2, 'Type': 'Talk', 'TidTalk': 'c'}]}}, b])
        self.assertEqual([e['raw_text'] for e in p.events], ['对白', '选择', '后续'])
        self.assertEqual([e['source_action'] for e in p.unverified_content], [a, b])

    def test_audio_shape_is_conservative(self):
        base = {'Name': 'SetAudioState', 'Params': {'AudioConfig': {'Group': 'g', 'State': 's'}}}
        self.assertTrue(flow_audio_state_shape(base))
        for bad in [dict(base, Async=True), dict(base, Condition={}),
                    {'Name': 'SetAudioState', 'Params': {'AudioConfig': {'Group': 'g', 'State': {}}}}]:
            self.assertFalse(flow_audio_state_shape(bad))
            p = Exporter(allow_incomplete=True); p.state_key = 'test'
            with self.assertRaises(ValueError): p.action(bad)
        p = Exporter(); p.state_key = 'test'
        with self.assertRaises(ValueError): p.action(base)
