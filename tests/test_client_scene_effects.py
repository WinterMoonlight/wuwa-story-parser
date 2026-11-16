import copy
import unittest

from wuwa_story.client_scene_effects import client_scene_shape, client_scene_evidence


class ClientSceneEffectsTests(unittest.TestCase):
    def base(self):
        return {'Name': 'ClientPreEnableSubLevels',
                'Params': {'EnableLevels': ['/Game/A'], 'DisableLevels': []}}

    def test_level_lists_and_callback_boundary(self):
        a = self.base()
        self.assertTrue(client_scene_shape(a))
        self.assertTrue(client_scene_shape({**a, 'Async': False}))
        for bad in ({**a, 'Async': True}, {**a, 'Callbacks': []},
                    {**a, 'Params': {**a['Params'], 'Actions': []}},
                    {**a, 'Params': {'EnableLevels': '/Game/A', 'DisableLevels': []}},
                    {**a, 'Params': {'EnableLevels': ['/Game/'], 'DisableLevels': []}}):
            self.assertFalse(client_scene_shape(bad))

    def test_capture_exact_fields_and_finite_delay(self):
        a = self.base()
        a['Params']['TransitionOption'] = {
            'Type': 'SceneCapture', 'DelayTime': 1.5, 'SceneCaptureEffect': '/Game/Fx.Fx'}
        self.assertTrue(client_scene_shape(a))
        for delay in (-1, float('inf'), float('nan'), True, '1.5'):
            bad = copy.deepcopy(a); bad['Params']['TransitionOption']['DelayTime'] = delay
            self.assertFalse(client_scene_shape(bad))
        bad = copy.deepcopy(a); bad['Params']['TransitionOption']['OnFinish'] = []
        self.assertFalse(client_scene_shape(bad))
        bad = copy.deepcopy(a); bad['Params']['TransitionOption']['Type'] = 'Other'
        self.assertFalse(client_scene_shape(bad))

    def test_toggle_boolean_only_and_evidence(self):
        for enabled in (True, False):
            a = {'Name': 'GiantToggleModel', 'Params': {'IsEnabled': enabled}}
            self.assertTrue(client_scene_shape(a))
            record = client_scene_evidence(a)
            self.assertIs(record['enabled'], enabled)
            self.assertFalse(record['runtime_completion_verified'])
            self.assertFalse(record['callbacks_verified'])
        for enabled in (1, 0, None, 'true'):
            self.assertFalse(client_scene_shape({'Name': 'GiantToggleModel', 'Params': {'IsEnabled': enabled}}))
        a = self.base(); record = client_scene_evidence(a)
        self.assertEqual(record['enable_levels'], ['/Game/A'])
        self.assertIsNone(record['transition'])
        self.assertFalse(record['wait_semantics_verified'])
        self.assertEqual(record['source_action'], a)
