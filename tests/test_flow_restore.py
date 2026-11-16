import unittest
from unittest.mock import patch
from wuwa_story.export_task import Exporter


class FlowRestoreTests(unittest.TestCase):
    def test_restore_keeps_dialogue_order_and_source(self):
        a = {'Name': 'ShowAllHidedGroupInFlow', 'Params': {}}
        p = Exporter(allow_incomplete=True)
        p.state_key = 'test'
        with patch('wuwa_story.export_task.texts', {'a': '之前', 'b': '之后'}):
            p.actions([{'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'a'}}, a,
                       {'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'b'}}])
        self.assertEqual([e['raw_text'] for e in p.events], ['之前', '之后'])
        self.assertEqual(p.unverified_content[0]['source_action'], a)

    def test_unknown_fields_async_and_strict_mode_rejected(self):
        for a in ({'Name': 'ShowAllHidedGroupInFlow', 'Params': {'Actions': []}},
                  {'Name': 'ShowAllHidedGroupInFlow', 'Async': True},
                  {'Name': 'ShowAllHidedGroupInFlow', 'Condition': {}}):
            with self.assertRaises(ValueError):
                p = Exporter(allow_incomplete=True); p.state_key = 'test'; p.action(a)
        with self.assertRaises(ValueError):
            p = Exporter(); p.state_key = 'test'; p.action({'Name': 'ShowAllHidedGroupInFlow'})
