import unittest
from wuwa_story.paths import DATABASE_DIR


@unittest.skipUnless((DATABASE_DIR / 'db_QuestData.db').exists(), 'Local ConfigDB required')
class ExternalContentTests(unittest.TestCase):
    def test_real_task_external_evidence_and_incomplete_status(self):
        from wuwa_story.export_task import Exporter
        result = Exporter(allow_incomplete=True).export(139000026)
        self.assertFalse(result['validation']['complete_for_supported_task_shape'])
        self.assertEqual(result['validation']['status'], 'needs_review')
        self.assertEqual(result['validation']['missing_text_ids'], [])
        self.assertEqual(result['validation']['confirmed_missing_text_ids'], [])
        self.assertTrue(result['validation']['known_text_references_complete'])
        self.assertTrue(result['validation']['unverified_content'])
        movie = next(e for e in result['events'] if e['kind'] == 'media_reference')['media']
        self.assertEqual(movie['cg_id'], 104)
        self.assertIn('Nvzhu', movie['asset_path'])
        self.assertEqual(movie['caption_status'], 'no_rows_not_proof_of_silence')
        self.assertEqual(movie['text_coverage'], 'additional_text_unverified')
        self.assertNotIn('gap', movie)
        tip = next(e for e in result['external_content'] if e['source_action']['Name'] == 'CommonTip')
        self.assertEqual(tip['route_scope'], 'failure_branch')
        self.assertNotIn(tip['texts'][0]['text_id'], [e.get('text_id') for e in result['events']])
        board = next(e for e in result['external_content'] if e['source_action']['Name'] == 'OpenSystemBoard')
        self.assertEqual(board['role_id'], 1202)
        self.assertEqual(board['owner']['name'], '炽霞')
        function = next(e for e in result['external_content'] if e['source_action']['Name'] == 'OpenSystemFunction')
        self.assertEqual(function['timing']['preceding_async_action_indices'], [1])
        self.assertFalse(function['timing']['completion_order_verified'])
        ui = result['task_ui_texts']
        self.assertTrue(any(t['source_path'][0] == 'UIConfig' for t in ui))
        self.assertTrue(any(t['source_path'][0] == 'OccupationConfig' for t in ui))
        self.assertTrue(any(t['visibility_flags'].get('HideUi') for t in ui))
        self.assertTrue(all('text' in t for t in ui))
        self.assertTrue(all(not t['display_verified'] for t in ui))
        self.assertTrue(board['texts'][0]['text'])
        self.assertTrue(any(a['Name'] == 'PlayFlow' for a in board['preceding_actions']))

    def test_failure_ancestor_and_ui_visibility_are_preserved(self):
        from wuwa_story.external import inspect_node_ui, node_context
        nodes = [{'Id': 9, 'Type': 'QuestFailed', 'ParentNodeId': 0},
                 {'Id': 2, 'Type': 'ChildQuest', 'ParentNodeId': 9,
                  'HideTip': True, 'TidTip': 'nonexistent-ui-reference'}]
        entry = inspect_node_ui(nodes)[0]
        self.assertEqual(entry['context']['route_scope'], 'failure_branch')
        self.assertTrue(entry['missing'])
        self.assertTrue(entry['visibility_flags']['HideTip'])
        with self.assertRaises(ValueError):
            node_context({'Id': 3, 'Type': 'ChildQuest', 'ParentNodeId': 4}, [])
        with self.assertRaises(ValueError):
            node_context({'Id': 9, 'Type': 'ChildQuest', 'ParentNodeId': 9},
                         [{'Id': 9, 'Type': 'ChildQuest', 'ParentNodeId': 9}])

    def test_strict_export_still_rejects_incomplete_task(self):
        from wuwa_story.export_task import Exporter
        with self.assertRaises(ValueError):
            Exporter().export(139000026)

    def test_movie_missing_reference_is_not_silent(self):
        from wuwa_story.external import inspect_movie
        with self.assertRaises(ValueError):
            inspect_movie('missing', lambda *args: [])

    def test_properties_require_matching_package_and_do_not_prove_silence(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from wuwa_story import external
        from wuwa_story.database import rows
        with tempfile.TemporaryDirectory() as temp, patch.object(external, 'WORK_DIR', Path(temp)):
            folder = Path(temp) / 'asset_exports/properties'
            folder.mkdir(parents=True)
            file = folder / 'M01012_Nvzhu.json'
            obj = {'Type': 'StreamMediaSource', 'Name': 'M01012_Nvzhu', 'Package': 'wrong/package',
                   'Properties': {'StreamUrl': 'filepath://./Aki/Movies/ZhanZhuang/M01012_Nvzhu.mp4'}}
            file.write_text(json.dumps([obj]), encoding='utf-8')
            self.assertNotIn('media_source_evidence', external.inspect_movie('C3jinzhoutexie', rows))
            obj['Package'] = 'Client/Content/Aki/Sequence/LevelB_Seq/Main/Section1/M01012/M01012_Nvzhu'
            file.write_text(json.dumps([obj]), encoding='utf-8')
            movie = external.inspect_movie('C3jinzhoutexie', rows)
            self.assertEqual(movie['media_source_evidence']['stream_url'], obj['Properties']['StreamUrl'])
            self.assertEqual(movie['text_coverage'], 'additional_text_unverified')

    def test_option_container_does_not_emit_stale_prompt(self):
        from wuwa_story.export_task import Exporter
        e = Exporter()
        e.state_key = 'test'
        e.text = lambda key: key
        e.talk([{'Id': 1, 'Type': 'Option', 'TidTalk': 'stale', 'PlotLineKey': '',
                 'Options': [{'TidTalkOption': 'choose'}]}])
        self.assertEqual([x['kind'] for x in e.events], ['choice'])
        self.assertEqual(e.talk_coverage[0]['non_dialogue_option_containers'][0]['TidTalk'], 'stale')
