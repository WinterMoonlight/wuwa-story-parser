import unittest
from unittest.mock import patch
from collections import Counter
from wuwa_story.paths import DATABASE_DIR


class MechanismTests(unittest.TestCase):
    def test_identical_arrays_only_and_conflicts_rejected(self):
        from wuwa_story.export_task import flow_actions
        actions = [{'Name': 'ShowTalk', 'Params': {'TalkItems': []}}]
        with patch('wuwa_story.export_task.embedded', return_value=[(1, actions), (6, actions)]):
            self.assertEqual(flow_actions(b''), (actions, [1, 6]))
        for entries in ([], [(1, actions), (6, [])]):
            with patch('wuwa_story.export_task.embedded', return_value=entries):
                with self.assertRaises(ValueError):
                    flow_actions(b'')

    def test_world_effect_unknown_shape_rejected(self):
        from wuwa_story.coverage import validate_world_effect
        validate_world_effect('SetReviveRegion', {'SetReviveType': 'Add', 'ReviveId': 1})
        for name, params in [('SetWeather', {'WeatherId': 1, 'TidText': 'unread'}),
                             ('SetPlayerOperationRestriction', {'Type': 'Unknown'}),
                             ('SetReviveRegion', {'SetReviveType': 'Unknown', 'ReviveId': 1})]:
            with self.assertRaises(ValueError):
                validate_world_effect(name, params)

    def test_acceptance_not_silently_executed(self):
        from wuwa_story.export_task import Exporter
        e = Exporter(allow_incomplete=True)
        e.state_key = 'test'
        e.action({'Name': 'AccpetCurrentQuest', 'Params': {}})
        self.assertEqual(e.events[0]['kind'], 'quest_control')
        self.assertEqual(e.unverified_content[0]['kind'], 'quest_acceptance')
        with self.assertRaises(ValueError):
            e.action({'Name': 'AccpetCurrentQuest', 'Params': {'QuestId': 1}})

    @unittest.skipUnless((DATABASE_DIR / 'db_QuestData.db').exists(), 'Local ConfigDB required')
    def test_real_upper_cross_task_export(self):
        from wuwa_story.export_task import Exporter
        d = Exporter(allow_incomplete=True).export(139000025)
        self.assertEqual(d['validation']['exported_flow_count'], 21)
        self.assertEqual(d['validation']['confirmed_missing_text_ids'], [])
        self.assertEqual(d['validation']['status'], 'needs_review')
        self.assertEqual(Counter(e['kind'] for e in d['events']),
                         {'dialogue': 182, 'choice': 32, 'media_reference': 1, 'quest_control': 1})
        self.assertEqual(len(d['task_ui_texts']), 47)
        self.assertEqual(Counter(e['source_action']['Name'] for e in d['external_content']),
                         {'GuideTrigger': 25, 'CompleteGuide': 23, 'OpenSystemFunction': 2})
        self.assertEqual({e['ui_label'] for e in d['external_content'] if 'ui_label' in e}, {'协奏作用', '锁定技能'})
        self.assertEqual(next(e['media']['cg_id'] for e in d['events'] if e['kind'] == 'media_reference'), 102)
        self.assertEqual(sum(len(s['equivalent_action_fields']) > 1 for s in d['source']['scenes']), 1)
        self.assertEqual(d['rendering']['gender'], 'female')
        with self.assertRaises(ValueError):
            Exporter().export(139000025)
