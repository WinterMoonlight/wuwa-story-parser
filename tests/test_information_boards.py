import unittest
from unittest.mock import patch
from wuwa_story.information_boards import inspect_information
from wuwa_story.database import rows
from wuwa_story.export_task import Exporter


class InformationBoardTests(unittest.TestCase):
    def test_four_real_titles_and_bodies(self):
        expected = ['《关于归墟港市的悲鸣事件提交的记录（十一）》', 'K626号决议',
                    '记录着平和思绪的片段', '未经授权审阅的日志文件']
        for i, title in enumerate(expected, 103000005):
            board = inspect_information(i, rows)
            self.assertEqual(board['texts'][0]['text'], title)
            self.assertGreater(len(board['texts'][1]['text']), 200)
            self.assertEqual(board['missing_text_ids'], [])

    def test_exact_id_missing_and_duplicate_are_not_guessed(self):
        with self.assertRaises(ValueError): inspect_information(1, lambda *args: [])
        with self.assertRaises(ValueError): inspect_information(True, rows)
        with self.assertRaises(ValueError):
            inspect_information(1, lambda *args: [{'Id': 1}, {'Id': 1}])

    def test_call_position_and_missing_text_preserved(self):
        p = Exporter(allow_incomplete=True); p.state_key = 'test'
        actions = [{'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'before'}},
                   {'Name': 'OpenSystemBoard', 'Params': {'SystemType': 'InformationView', 'BoardId': 103000006}},
                   {'Name': 'ShowCenterText', 'Params': {'TidCenterText': 'after'}}]
        p.actions(actions)
        self.assertEqual([e['kind'] for e in p.events], ['narration', 'information_board', 'narration'])
        self.assertIn('K626号决议', p.events[1]['raw_text'])
        with patch('wuwa_story.information_boards.texts', {}):
            board = inspect_information(103000006, rows)
        self.assertEqual(len(board['missing_text_ids']), 2)
        self.assertIsNone(board['texts'][1]['raw_text'])
