import unittest
from copy import deepcopy
from unittest.mock import patch
from wuwa_story.sublevels import switch_shape, switch_evidence
from wuwa_story.export_task import Exporter


class SublevelTests(unittest.TestCase):
    def test_wait_flags_not_assumed(self):
        a = {'Name': 'SwitchSubLevels', 'Params': {'Type': 'Directly', 'LoadLevels': ['/Game/a'], 'UnloadLevels': []}}
        self.assertTrue(switch_shape(a))
        self.assertIsNone(switch_evidence(a)['wait_for_completion'])
        for v in (False, True):
            b = deepcopy(a); b['Params']['IsWaitForSwitchComplete'] = v
            self.assertTrue(switch_shape(b))
            self.assertIs(switch_evidence(b)['wait_for_completion'], v)
            self.assertFalse(switch_evidence(b)['streaming_completion_verified'])
        for key, value in [('Callbacks', []), ('IsWaitForSwitchComplete', 1), ('LoadLevels', [1])]:
            b = deepcopy(a); b['Params'][key] = value
            self.assertFalse(switch_shape(b))
        self.assertFalse(switch_shape(dict(a, Async=True)))

    def test_call_order_and_strict_boundary(self):
        a = {'Name': 'SwitchSubLevels', 'Params': {'Type': 'Directly', 'LoadLevels': [], 'UnloadLevels': ['/Game/a']}}
        p = Exporter(allow_incomplete=True); p.state_key = 'test'
        with patch('wuwa_story.export_task.texts', {'a': '前', 'b': '后'}):
            p.actions([{'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'a'}}, a,
                       {'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'b'}}])
        self.assertEqual([e['raw_text'] for e in p.events], ['前', '后'])
        self.assertFalse(p.unverified_content[0]['callbacks_verified'])
        p = Exporter(); p.state_key = 'test'
        with self.assertRaises(ValueError): p.action(a)
