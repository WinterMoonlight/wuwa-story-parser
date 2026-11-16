import unittest
import struct
from unittest.mock import patch
from wuwa_story.database import rows, field
from wuwa_story.captions import decode_captions
from wuwa_story.external import inspect_movie


class CaptionTests(unittest.TestCase):
    def setUp(self):
        self.rows = [r for r in rows('db_cgVedio.db', 'videocaption') if r['CgName'] == 'M0391']

    def test_real_text_and_order_independent_of_row_order(self):
        result = decode_captions('M0391', list(reversed(self.rows)))
        self.assertEqual([c['caption_id'] for c in result['captions']], list(range(1957, 1967)))
        self.assertTrue(result['caption_order_consensus'])
        self.assertFalse(result['caption_order_evidence']['time_unit_verified'])
        self.assertFalse(result['caption_order_evidence']['runtime_playback_verified'])
        self.assertEqual(result['caption_missing_text_ids'], [])
        self.assertEqual(result['captions'][-1]['text'], '御者，城中佳夜已至，同我赴这场朝月喜事吧。')

    def test_disagreement_or_tie_is_not_sorted_as_verified(self):
        for value in (100000, 1480):
            changed = [dict(r) for r in self.rows]
            b = bytearray(changed[0]['BinData'])
            struct.pack_into('<i', b, field(b, 2), value)
            changed[0]['BinData'] = bytes(b)
            self.assertFalse(decode_captions('M0391', changed)['caption_order_consensus'])

    def test_missing_text_stays_missing_without_guessing(self):
        with patch('wuwa_story.captions.texts', {}):
            result = decode_captions('M0391', self.rows)
        self.assertEqual(len(result['caption_missing_text_ids']), 10)
        self.assertEqual(result['captions'][0]['text'], '[缺失字幕正文]')

    def test_invalid_blob_keeps_movie_unparsed(self):
        def read(file, table):
            if table == 'videocaption':
                return [{'CgName': 'M0391', 'CaptionId': 1957, 'BinData': b'bad'}]
            return rows(file, table)
        movie = inspect_movie('M0391', read)
        self.assertEqual(movie['text_coverage'], 'known_caption_rows_unparsed')
        self.assertIn('caption_decode_error', movie)
