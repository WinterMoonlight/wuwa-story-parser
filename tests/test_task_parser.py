import unittest
from wuwa_story.paths import DATABASE_DIR

HAS_DATA = DATABASE_DIR.joinpath('db_QuestTree.db').exists()
if HAS_DATA:
    from wuwa_story.export_task import Exporter, choose_option
    from wuwa_story.speakers import SpeakerResolver
    from wuwa_story.database import rows, embedded


@unittest.skipUnless(HAS_DATA, 'Local ConfigDB required')
class TaskParserTests(unittest.TestCase):
    def test_name_fallback(self):
        resolver = SpeakerResolver()
        self.assertEqual(resolver.records[1424]['name'], '妮娅')
        self.assertEqual(resolver.records[1424]['source'], 'BinData.Name(field3)')
        self.assertEqual(resolver.records[108]['name'], '秧秧')

    def test_real_config_actor_continuity(self):
        resolver = SpeakerResolver()
        key = '剧情_3_5_玄方城_秧秧_2_1_10'
        blob = next(r['BinData'] for r in rows('db_flowState.db', 'flowstate') if r['StateKey'] == key)
        def walk(value):
            if isinstance(value, dict):
                yield value
                for child in value.values():
                    yield from walk(child)
            elif isinstance(value, (list, tuple)):
                for child in value:
                    yield from walk(child)
        controls = [o for o in walk(embedded(blob)) if o.get('Name') in ('BeginFlowTemplate', 'ChangeActorTalker')]
        self.assertEqual([o['Name'] for o in controls], ['BeginFlowTemplate', 'ChangeActorTalker', 'ChangeActorTalker'])
        resolver.begin(controls[0]['Params'], {'state_key': key})
        self.assertTrue(resolver.change(controls[1]['Params'], {'state_key': key}))
        result = resolver.identify(849)
        self.assertEqual(result['display_name'], '？？')
        self.assertEqual(result['resolved_speaker_id'], 350101)
        self.assertTrue(resolver.change(controls[2]['Params'], {'state_key': key}))
        self.assertIsNone(resolver.identify(849)['resolved_speaker_id'])

    def test_shared_anonymous_label_is_not_resolved(self):
        resolver = SpeakerResolver()
        resolver.begin({'Actors': [{'TalkerId': 108}, {'TalkerId': 877}]}, {})
        resolver.change({'ActorIndex': 0, 'Talker': 178}, {})
        resolver.change({'ActorIndex': 1, 'Talker': 178}, {})
        self.assertIsNone(resolver.identify(178)['resolved_speaker_id'])

    def test_real_task_both_routes(self):
        a = Exporter().export(211750002)
        key = a['route']['choices'][0]['choice_key']
        b = Exporter({key: 1}).export(211750002)
        akeys = [e['text_id'] for e in a['events']]
        bkeys = [e['text_id'] for e in b['events']]
        self.assertIn('Event_WWPDJSBF_4_4', akeys)
        self.assertNotIn('Event_WWPDJSBF_4_5', akeys)
        self.assertIn('Event_WWPDJSBF_4_5', bkeys)
        self.assertNotIn('Event_WWPDJSBF_4_4', bkeys)
        self.assertEqual(a['events'][3:], b['events'][3:])
        self.assertEqual(len(a['route']['choices']), 7)
        self.assertEqual(len(a['events']), 29)
        self.assertEqual(a['validation']['missing_text_ids'], [])
        self.assertEqual(a['events'][0]['display_name'], '？？？')
        self.assertIsNone(a['events'][0]['resolved_speaker_id'])

    def test_unsupported_condition_rejected(self):
        with self.assertRaises(ValueError):
            choose_option([{'TidTalkOption': 'example', 'Condition': {'Type': 'Unknown'}}])

    def test_mainline_handbook_coverage_and_branch(self):
        result = Exporter().export(880000013)
        self.assertEqual(result['source']['quest_definition']['Type'], 1)
        self.assertEqual(result['validation']['missing_text_ids'], [])
        scenes = result['source']['scenes']
        self.assertEqual([s['task_node_ids'] for s in scenes], [[2], [5], [6], [7]])
        self.assertEqual(result['validation']['referenced_flow_count'], 4)
        self.assertEqual(len(result['events']), 145)
        self.assertEqual(len(result['route']['choices']), 18)
        self.assertEqual([e['sequence'] for e in result['events']], list(range(1, 146)))
        for scene in scenes:
            events = result['events'][scene['event_start']:scene['event_end_exclusive']]
            self.assertTrue(events)
            self.assertTrue(all(e['state_key'] == scene['state_key'] for e in events))
        key = result['route']['choices'][2]['choice_key']
        alternate = Exporter({key: 1}).export(880000013)
        default_ids = {e['text_id'] for e in result['events']}
        alternate_ids = {e['text_id'] for e in alternate['events']}
        self.assertIn('Chengxiaoshan_main_1_1_1_2_3', default_ids - alternate_ids)
        self.assertIn('Chengxiaoshan_main_1_1_1_2_6', alternate_ids - default_ids)
        self.assertEqual(result['events'][-1]['text_id'], alternate['events'][-1]['text_id'])

    def test_handbook_missing_reference_rejected(self):
        from unittest.mock import patch
        from wuwa_story import export_task
        original = export_task.flow_key
        # Alter the first handbook reference only, leaving task references intact.
        calls = 0
        def changed(flow):
            nonlocal calls
            calls += 1
            return 'missing_state' if calls == 1 else original(flow)
        with patch.object(export_task, 'flow_key', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'cover task flow references'):
                Exporter().export(880000013)


if __name__ == '__main__':
    unittest.main()
