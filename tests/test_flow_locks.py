import unittest
from unittest.mock import patch
from wuwa_story.reading_effects import flow_lock_shape
from wuwa_story.export_task import Exporter


class FlowLockTests(unittest.TestCase):
    def test_order_and_recording(self):
        p = Exporter(allow_incomplete=True); p.state_key = 'test'
        locks = [{'Name': 'SetTimeLockState', 'Params': {'LockState': v}} for v in ('Lock', 'Unlock')]
        with patch('wuwa_story.export_task.texts', {'a': '前', 'b': '后'}):
            p.actions([locks[0], {'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'a'}},
                       locks[1], {'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'b'}}])
        self.assertEqual([e['raw_text'] for e in p.events], ['前', '后'])
        self.assertEqual([e['source_action'] for e in p.unverified_content], locks)

    def test_unknown_states_and_runtime_controls_rejected(self):
        for name in ('SetTimeLockState', 'SetWeatherLockState'):
            a = {'Name': name, 'Params': {'LockState': 'Lock'}}
            self.assertTrue(flow_lock_shape(a))
            for bad in [dict(a, Async=True), dict(a, Condition={}),
                        {'Name': name, 'Params': {'LockState': 'Toggle'}},
                        {'Name': name, 'Params': {'LockState': 'Lock', 'Actions': []}}]:
                self.assertFalse(flow_lock_shape(bad))
                p = Exporter(allow_incomplete=True); p.state_key = 'test'
                with self.assertRaises(ValueError): p.action(bad)
            p = Exporter(); p.state_key = 'test'
            with self.assertRaises(ValueError): p.action(a)
