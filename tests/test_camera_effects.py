import unittest
from unittest.mock import patch
from wuwa_story.camera_effects import camera_shape
from wuwa_story.export_task import Exporter


class CameraTests(unittest.TestCase):
    def test_finite_timeout_audit_and_unknown_variant(self):
        a={'Name':'PlayerLookAt','Params':{'Pos':{'X':1,'Y':2,'Z':3},'CameraMove':True},'Timeout':5}
        p=Exporter(allow_incomplete=True);p.state_key='test';p.action(a)
        self.assertEqual(p.unverified_content[0]['timeout_seconds'],5)
        self.assertFalse(p.unverified_content[0]['deadline_outcome_verified'])
        a['Params']['PlayAnimation']=True;self.assertTrue(camera_shape(a))
        p.action(a)
        self.assertFalse(p.unverified_content[-1]['animation_completion_verified'])
        for value in [1, 'true', None, {}]:
            a['Params']['PlayAnimation']=value;self.assertFalse(camera_shape(a))

    def test_real_look_at_animation_restores_known_text_only(self):
        from wuwa_story.recap_backbone import export_task_backbone
        d=export_task_backbone(168800009)
        segment=next(s for s in d['recap_backbone']['segments'] if s['state_key']=='剧情_3_2_拉海洛主线_上半_暗面2_18_1')
        self.assertEqual(segment['status'],'parsed')
        self.assertEqual(len(segment['events']),4)
        self.assertTrue(any(e.get('play_animation') is True for e in segment['unverified_content']))

    def test_adjustment_numeric_payload_and_unknown_content(self):
        o = {'Type': '关卡.Common.镜头调整', 'Priority': 100, 'FadeInTime': 0.5,
             'FadeOutTime': 1, 'ArmLength': 300, 'MinumArmLength': 300, 'MaxiumArmLength': 300,
             'Offset': {'Z': 2}, 'Fov': 75, 'OverlayArmLength': 0,
             'FadeInCurve': {'Type': 4, 'N': 2}}
        a = {'Name': 'AdjustPlayerCamera', 'Params': {'Option': o}}
        self.assertTrue(camera_shape(a))
        self.assertTrue(camera_shape(dict(a, Timeout=0)))
        self.assertTrue(camera_shape(dict(a, Timeout=0.5)))
        for value in [-1, True, float('inf'), float('nan'), '5']:
            self.assertFalse(camera_shape(dict(a, Timeout=value)))
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
