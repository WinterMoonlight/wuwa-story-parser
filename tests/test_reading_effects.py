import unittest
from wuwa_story.reading_effects import validate_reading_effect
from wuwa_story.coverage import audit_task
from wuwa_story.blockers import assess_actions, compare


class ReadingEffectsTests(unittest.TestCase):
    def test_optional_visibility_lists_and_flags(self):
        for flag in ({}, {'IsHidePasserByNpc': False}):
            self.assertTrue(validate_reading_effect('HideGroup', {
                'GroupKey': 'sample', 'HideConfig': {'Type': 'WorldEntityAndLevelPlay',
                'HideRangeEntities': [], 'ExcludeEntities': [2], 'AppendLevelPlays': [3]}, **flag}))

    def test_unknown_semantics_or_nested_payload_rejected(self):
        for cfg in [
            {'Type': 'SpecifyEntity', 'EntityIds': [True]},
            {'Type': 'SpecifyEntity', 'EntityIds': [1], 'ForceClean': True},
            {'Type': 'SpecifyLevelPlay', 'LevelPlays': [1]},
            {'Type': 'WorldEntityAndLevelPlay', 'HideRangeEntities': [{'FlowId': 1}]},
            {'Type': 'SpecifyEntity', 'EntityIds': [1], 'Actions': []},
        ]:
            with self.assertRaises(ValueError):
                validate_reading_effect('HideGroup', {'GroupKey': 'x', 'HideConfig': cfg})
        with self.assertRaises(ValueError):
            validate_reading_effect('SetAudioState', {'AudioConfig': {'Group': 'g', 'State': {'FlowId': 1}}})

    def test_reading_only_and_preserves_runtime_caveat(self):
        action = {'Name': 'SetAudioState', 'Params': {'AudioConfig': {'Group': 'g', 'State': 's'}}}
        nodes = [{'Type': 'Sequence', 'Id': 1, 'ParentNodeId': 0},
                 {'Type': 'QuestSucceed', 'Id': 2, 'ParentNodeId': 1, 'FinishActions': [action]}]
        with self.assertRaises(ValueError):
            audit_task({}, nodes)
        audit = audit_task({}, nodes, reading_projection=True)
        self.assertEqual(audit['reading_effects'][0]['params'], action['Params'])
        self.assertFalse(audit['reading_effects'][0]['indirect_trigger_effects_verified'])

    def test_all_blockers_not_only_first(self):
        actions = [{'Name': n, 'Params': {}} for n in ['SetAudioState', 'HideGroup', 'UnknownAction']]
        report = assess_actions({}, [{'Id': 1, 'Actions': actions}])
        self.assertEqual(len(report['issues']), 3)

    def test_error_movement_is_not_gain(self):
        def report(error):
            return {'summary': {}, 'tasks': [{'quest_id': 1, 'title': 'x', 'status': 'inventory_only',
                    'gaps': [{'kind': 'route_blocked', 'detail': error}]}]}
        delta = compare(report('HideGroup'), report('UnknownAction'))
        self.assertEqual(len(delta['first_error_changes']), 1)
        self.assertEqual(delta['new_ordered_tasks'], [])
