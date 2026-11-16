import unittest
from unittest.mock import patch
from wuwa_story.performance_sources import sequence_source
from wuwa_story.external import inspect_movie
from wuwa_story.database import rows


class PerformanceSourcesTests(unittest.TestCase):
    def test_similar_filename_does_not_link_video(self):
        row = {'BinData': b'x', 'CgId': 1, 'CgName': 'M', 'GirlOrBoy': 0}
        with patch('wuwa_story.performance_sources.string', return_value='/other/X.X'):
            result = sequence_source('/Game/X.X', lambda *args: [row])
        self.assertEqual(result['video_matches'], [])
        self.assertNotIn('media', result)
        self.assertFalse(result['silence_verified'])

    def test_only_exact_female_link_resolves_captions(self):
        row = {'BinData': b'x', 'CgId': 1, 'CgName': 'M', 'GirlOrBoy': 0}
        with patch('wuwa_story.performance_sources.string', return_value='/Game/X.X'), \
             patch('wuwa_story.external.inspect_movie', return_value={
                 'asset_path': '/Game/X.X', 'text_coverage': 'configured_captions_read'}) as movie:
            result = sequence_source('/Game/X.X', lambda *args: [row])
            self.assertIn('media', result)
            sequence_source('/Game/X.X', lambda *args: [row, row])
            self.assertEqual(movie.call_count, 1)

    def test_real_movies_distinguish_caption_and_audio_sources(self):
        absent = inspect_movie('M0242', rows)
        known = inspect_movie('M0248', rows)
        self.assertEqual(absent['caption_row_count'], 0)
        self.assertFalse(absent['silence_verified'])
        self.assertTrue(absent['sound_sources'])
        self.assertFalse(absent['sound_sources'][0]['text_decoded'])
        self.assertEqual(len(known['captions']), 13)
        self.assertTrue(known['caption_order_consensus'])
