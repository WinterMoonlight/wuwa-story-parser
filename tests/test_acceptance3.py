import unittest
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.reading import reading_text


class ReadingDisplayTests(unittest.TestCase):
    def test_reading_removes_known_style_and_preserves_annotation(self):
        result=export_task_backbone(139000025)
        event=next(e for e in result['events']if '<ano=盘古终端>' in e.get('raw_text',''))
        self.assertIn('<color=Highlight>',event['text'])
        text=reading_text(result)
        self.assertIn('葫芦〔盘古终端〕',text)
        self.assertNotIn('<color=Highlight>',text)
        self.assertNotIn('<ano=',text)

    def test_configured_empty_name_is_distinct_from_unknown_identity(self):
        from wuwa_story.speakers import SpeakerResolver
        resolver=SpeakerResolver()
        empty=resolver.identify(83)
        self.assertEqual(empty['identity_status'],'configured_empty_name')
        self.assertEqual(empty['display_name'],'无署名')
        self.assertIsNone(empty['resolved_speaker_id'])
        self.assertNotEqual(resolver.identify(999999999)['identity_status'],'configured_empty_name')

    def test_simulation_dungeon_dialogue_has_explicit_ownership(self):
        result=export_task_backbone(139000027)
        records=[r for r in result['batch_coverage']['records']
                 if r.get('origin','').endswith('_8_1') and r.get('reading_context')=='declared_levelplay_candidate']
        self.assertTrue(records)
        self.assertTrue(all(r['category']=='candidate_branch' and not r['order_verified'] for r in records))
        self.assertTrue(any('模拟领域' in r['text'] for r in records))
        links=result['batch_coverage']['declared_levelplay_links']
        self.assertTrue(any(link.get('dungeon_link',{}).get('dungeon_id')==1505 for link in links))


if __name__=='__main__':unittest.main()
