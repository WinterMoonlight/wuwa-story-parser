import unittest
from unittest.mock import patch
from wuwa_story.camera_effects import camera_shape
from wuwa_story.export_task import Exporter


class CameraTests(unittest.TestCase):
    def test_adjustment_numeric_payload_and_unknown_content(self):
        o = {'Type': '关卡.Common.镜头调整', 'Priority': 100, 'FadeInTime': 0.5,
             'FadeOutTime': 1, 'ArmLength': 300, 'MinumArmLength': 300, 'MaxiumArmLength': 300,
             'Offset': {'Z': 2}, 'Fov': 75, 'OverlayArmLength': 0,
             'FadeInCurve': {'Type': 4, 'N': 2}}
        a = {'Name': 'AdjustPlayerCamera', 'Params': {'Option': o}}
        self.assertTrue(camera_shape(a))
        self.assertTrue(camera_shape(dict(a, Timeout=0)))
        self.assertFalse(camera_shape(dict(a, Timeout=0.5)))
        o['Actions'] = []
        self.assertFalse(camera_shape(a)); del o['Actions']
        o['Fov'] = float('nan')
        self.assertFalse(camera_shape(a))
        a = {'Name': 'RestorePlayerCameraAdjustment', 'Params': {
            'ResetFocus': {'FadeInTime': 1, 'FadeInCurve': {'Type': 2, 'N': 2}}}}
        self.assertTrue(camera_shape(a))
        a['Params']['ResetFocus']['FadeInCurve']['Type'] = 99
        self.assertFalse(camera_shape(a))

    def test_shapes_are_restricted(self):
        good = {'Name': 'PlayerLookAt', 'Params': {'Pos': {'X': 1, 'Y': 2, 'Z': 3}, 'CameraMove': True}}
        self.assertTrue(camera_shape(good))
        self.assertFalse(camera_shape(dict(good, Async=True)))
        self.assertFalse(camera_shape(dict(good, Condition={})))
        self.assertFalse(camera_shape({'Name': 'PlayerLookAt', 'Params': {'Pos': {'X': True, 'Y': 2, 'Z': 3}, 'CameraMove': True}}))
        self.assertTrue(camera_shape({'Name': 'RestorePlayerCameraAdjustment'}))
        self.assertFalse(camera_shape({'Name': 'RestorePlayerCameraAdjustment', 'Params': {'ResetFocus': {}}}))
        self.assertTrue(camera_shape({'Name': 'ResetPlayerCameraFocus', 'Params': {'FadeInTime': 1, 'ResetType': {'Type': 'ResetToDefaultDirection'}}}))

    def test_order_and_strict_boundary(self):
        p = Exporter(allow_incomplete=True); p.state_key = 'test'
        a = {'Name': 'RestorePlayerCameraAdjustment', 'Params': {}}
        with patch('wuwa_story.export_task.texts', {'a': '之前', 'b': '之后'}):
            p.actions([{'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'a'}}, a,
                       {'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'b'}}])
        self.assertEqual([e['raw_text'] for e in p.events], ['之前', '之后'])
        self.assertEqual(p.unverified_content[0]['source_action'], a)
        p = Exporter(); p.state_key = 'test'
        with self.assertRaises(ValueError): p.action(a)
