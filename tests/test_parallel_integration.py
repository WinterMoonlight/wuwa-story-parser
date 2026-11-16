import unittest
from unittest.mock import patch
from wuwa_story.export_task import Exporter


class ParallelIntegrationTests(unittest.TestCase):
    def test_client_effects_preserve_order_and_strict_boundary(self):
        effects = [
            {'Name': 'ClientPreEnableSubLevels', 'Params': {'EnableLevels': ['/Game/A'], 'DisableLevels': []}},
            {'Name': 'GiantToggleModel', 'Params': {'IsEnabled': True}},
        ]
        for effect in effects:
            p = Exporter(allow_incomplete=True); p.state_key = 'test'
            with patch('wuwa_story.export_task.texts', {'a': 'before', 'b': 'after'}):
                p.actions([{'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'a'}}, effect,
                           {'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'b'}}])
            self.assertEqual([e['raw_text'] for e in p.events], ['before', 'after'])
            self.assertFalse(p.unverified_content[0]['runtime_completion_verified'])
            strict = Exporter(); strict.state_key = 'test'
            with self.assertRaises(ValueError): strict.action(effect)

    def test_unbound_actor_keeps_explicit_identity_and_context_does_not_leak(self):
        change = {'Name': 'ChangeActorTalker', 'Params': {'ActorIndex': 0, 'Talker': 2}}
        talk = {'Name': 'ShowTalk', 'Params': {'TalkItems': [
            {'Id': 1, 'Type': 'Talk', 'WhoId': 1, 'TidTalk': 'a', 'Actions': [change]},
            {'Id': 2, 'Type': 'Talk', 'WhoId': 2, 'TidTalk': 'b'}]}}
        names = {1: {'name': '???', 'source': 'test'}, 2: {'name': 'Known', 'source': 'test'}}
        p = Exporter(allow_incomplete=True, speaker_records=names); p.state_key = 'test'
        with patch('wuwa_story.export_task.texts', {'a': 'before', 'b': 'after'}):
            p.action(talk)
        self.assertEqual([e['display_name'] for e in p.events], ['???', 'Known'])
        self.assertIsNone(p.events[0]['resolved_speaker_id'])
        self.assertEqual(p.speakers.actors, [])
        self.assertFalse(p.unverified_content[0]['binding_resolved'])
        with self.assertRaises(ValueError): p.action(change)
        strict = Exporter(speaker_records=names); strict.state_key = 'test'
        with patch('wuwa_story.export_task.texts', {'a': 'before', 'b': 'after'}):
            with self.assertRaises(ValueError): strict.action(talk)
