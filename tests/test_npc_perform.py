import unittest
from unittest.mock import patch
from wuwa_story.npc_perform import npc_perform_shape
from wuwa_story.export_task import Exporter


class NpcPerformTests(unittest.TestCase):
    def test_shape_boundaries(self):
        for kind, key, expected in [(0, 'pose', True), (1, '', True), (7, 'pose', True),
                                     (7, '', False), (7, ' ', False), (8, 'pose', False),
                                     (0, '', False), (True, '', False), (1, 'pose', False)]:
            a = {'Name': 'FlowDefineNpcGroupPerform', 'Params': {'PerformType': {'Type': kind, 'Key': key}}}
            self.assertEqual(npc_perform_shape(a), expected)
            self.assertFalse(npc_perform_shape(dict(a, Async=True)))
            self.assertFalse(npc_perform_shape(dict(a, Callbacks=[])))

    def test_order_and_strict_mode(self):
        a = {'Name': 'FlowDefineNpcGroupPerform', 'Params': {'PerformType': {'Type': 0, 'Key': 'pose'}}}
        p = Exporter(allow_incomplete=True); p.state_key = 'test'
        with patch('wuwa_story.export_task.texts', {'a': '前', 'b': '后'}):
            p.actions([{'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'a'}}, a,
                       {'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'b'}}])
        self.assertEqual([e['raw_text'] for e in p.events], ['前', '后'])
        self.assertFalse(p.unverified_content[0]['callbacks_verified'])
        p = Exporter(); p.state_key = 'test'
        with self.assertRaises(ValueError): p.action(a)

    def test_type7_configuration_order_and_unknown_semantics(self):
        a = {'Name': 'FlowDefineNpcGroupPerform',
             'Params': {'PerformType': {'Type': 7, 'Key': 'arbitrary_key'}}}
        p = Exporter(allow_incomplete=True); p.state_key = 'test'
        with patch('wuwa_story.export_task.texts', {'a': '前', 'b': '后'}):
            p.actions([{'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'a'}}, a,
                       {'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'b'}}])
        self.assertEqual([e['raw_text'] for e in p.events], ['前', '后'])
        self.assertEqual(p.unverified_content[0]['source_action'], a)
        for key in ('enum_semantics_verified', 'runtime_completion_verified',
                    'asset_content_verified', 'callbacks_verified'):
            self.assertIs(p.unverified_content[0][key], False)
        strict = Exporter(); strict.state_key = 'test'
        with self.assertRaises(ValueError): strict.action(a)
        for extra in ({'Callbacks': []}, {'Condition': {}}, {'Actions': []}):
            bad = {**a, 'Params': {**a['Params'], **extra}}
            with self.assertRaises(ValueError): p.action(bad)
