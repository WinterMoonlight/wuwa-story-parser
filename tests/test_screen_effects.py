import unittest
from unittest.mock import patch
from wuwa_story.screen_effects import screen_stop_shape
from wuwa_story.export_task import Exporter


class ScreenEffectTests(unittest.TestCase):
    def test_shape_and_unknown_callbacks(self):
        a = {'Name': 'StopUiScreenEffect', 'Params': {'EffectDaPath': '/Game/Effect/A.A'}}
        self.assertTrue(screen_stop_shape(a))
        for bad in [dict(a, Async=True), dict(a, OnFinish=[]),
                    {'Name': 'StopUiScreenEffect', 'Params': {'EffectDaPath': ''}},
                    {'Name': 'StopUiScreenEffect', 'Params': {'EffectDaPath': '/Game/A', 'Actions': []}}]:
            self.assertFalse(screen_stop_shape(bad))

    def test_order_and_strict_boundary(self):
        a = {'Name': 'StopUiScreenEffect', 'Params': {'EffectDaPath': '/Game/Effect/A.A'}}
        p = Exporter(allow_incomplete=True); p.state_key = 'test'
        with patch('wuwa_story.export_task.texts', {'a': '前', 'b': '后'}):
            p.actions([{'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'a'}}, a,
                       {'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'b'}}])
        self.assertEqual([e['raw_text'] for e in p.events], ['前', '后'])
        self.assertFalse(p.unverified_content[0]['callbacks_verified'])
        p = Exporter(); p.state_key = 'test'
        with self.assertRaises(ValueError): p.action(a)
