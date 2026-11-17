import unittest
from unittest.mock import patch

from wuwa_story.speakers import SpeakerResolver
from wuwa_story.inventory_speakers import inventory_identity


class EmptySpeakerTests(unittest.TestCase):
    def test_explicit_empty_differs_from_missing_and_anonymous(self):
        records = {
            83: {'name': '', 'source': 'NameStringKey', 'configured_empty_name': True},
            84: {'name': '', 'source': 'unresolved'},
            85: {'name': '？？？', 'source': 'NameStringKey'},
        }
        resolver = SpeakerResolver(records)
        empty = resolver.identify(83)
        self.assertEqual(empty['display_name'], '无署名')
        self.assertEqual(empty['identity_status'], 'configured_empty_name')
        self.assertIsNone(empty['resolved_speaker_id'])
        self.assertEqual(resolver.identify(84)['identity_status'], 'unresolved')
        self.assertEqual(resolver.identify(85)['display_name'], '？？？')
        inventory = inventory_identity('TidTalk', {'WhoId': 83}, resolver, None)
        self.assertEqual(inventory['identity_status'], empty['identity_status'])
        self.assertEqual(inventory['display_name'], '无署名')

    def test_empty_mapping_requires_present_text_key(self):
        def source_rows(database, table):
            if database.startswith('zh-Hans'):
                return [{'Id': 1, 'Content': 'Speaker_empty_Name'},
                        {'Id': 2, 'Content': 'Speaker_missing_Name'}]
            return [{'Id': 83, 'NameStringKey': 1, 'BinData': b'empty'},
                    {'Id': 84, 'NameStringKey': 2, 'BinData': b'missing'}]
        with patch('wuwa_story.speakers.rows', side_effect=source_rows), \
                patch('wuwa_story.speakers.integer', return_value=-1), \
                patch('wuwa_story.speakers.texts', {'Speaker_empty_Name': ''}):
            resolver = SpeakerResolver()
        self.assertEqual(resolver.identify(83)['identity_status'], 'configured_empty_name')
        self.assertEqual(resolver.identify(84)['identity_status'], 'unresolved')

    def test_real_empty_speakers_and_explicit_narrator(self):
        resolver = SpeakerResolver()
        empty = {sid for sid, record in resolver.records.items()
                 if record.get('configured_empty_name') is True}
        self.assertEqual(empty, {83, 1066})
        self.assertEqual(resolver.identify(83)['name_source']['name_text_id'], 'Speaker_83_Name')
        self.assertEqual(resolver.identify(100075)['display_name'], '旁白')
        self.assertIsNone(resolver.identify(83)['resolved_speaker_id'])


if __name__ == '__main__':
    unittest.main()
