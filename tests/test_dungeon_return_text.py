import unittest
from copy import deepcopy
from wuwa_story.dungeon_return_text import dungeon_return_sections


class DungeonReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from wuwa_story.batch import Snapshot
        from wuwa_story.database import embedded
        from wuwa_story.dungeon_candidates import dungeon_candidates
        cls.source = Snapshot()
        cls.nodes = [embedded(row['BinData'])[0][1] for row in cls.source.rows('db_QuestNodeData.db', 'questnodedata')
                     if row['Key'].startswith('139000027_')]
        books = [row for row in cls.source.rows('db_PlotHandBook.db', 'plothandbookconfig') if row['QuestId'] == 139000027]
        cls.result = {'source': {'quest_definition': {'DungeonId': 8},
                                'order_source': {'entries': embedded(books[0]['BinData'])[0][1]}},
                      'events': [{'state_key': '剧情_新主线_CE版_第一章_第二幕_安此亿兆生_1_26'}]}
        cls.audits = dungeon_candidates(cls.nodes, cls.source)[2]

    def test_real_sections_are_separate_local_evidence(self):
        sections = dungeon_return_sections(self.result, self.nodes, self.audits, self.source)
        self.assertEqual([(section['scope'], len(section['events'])) for section in sections], [
            ('before_explicit_dungeon_completion', 4), ('success_transition', 1)])
        self.assertTrue(all(section['entry_index'] == 44 for section in sections))
        self.assertTrue(all(not section['proof']['relative_section_order_verified'] for section in sections))
        self.assertIn('告诉了秧秧与白芷', sections[1]['events'][0]['text'])
        self.assertEqual(sections[0]['placement'], 'body')
        self.assertEqual(sections[0]['insert_before_event'], 0)
        self.assertEqual(sections[1]['placement'], 'supplement')
        self.assertEqual(sections[1]['proof']['destination_map_id'], 2502)

    def test_async_dialogue_cannot_supply_completion_boundary(self):
        audits = deepcopy(self.audits)
        node = next(node for node in audits[0]['nodes'] if node['Id'] == 37)
        node['FinishActions'][3]['Async'] = True
        sections = dungeon_return_sections(self.result, self.nodes, audits, self.source)
        self.assertEqual([section['scope'] for section in sections], ['success_transition'])

    def test_repeated_tip_does_not_supply_unique_location(self):
        result = deepcopy(self.result)
        entry = next(entry for entry in result['source']['order_source']['entries']
                     if entry.get('TidTip') == next(node['TidTip'] for node in self.nodes if node['Id'] == 281))
        result['source']['order_source']['entries'].append(entry)
        self.assertEqual(dungeon_return_sections(result, self.nodes, self.audits, self.source), [])

    def test_unknown_destination_rejects_transition_text(self):
        audits = deepcopy(self.audits)
        success = next(node for node in audits[0]['nodes'] if node['Type'] == 'QuestSucceed')
        success['FinishActions'][1]['Params']['DungeonId'] = 999999999
        sections = dungeon_return_sections(self.result, self.nodes, audits, self.source)
        self.assertEqual([section['scope'] for section in sections], ['before_explicit_dungeon_completion'])


if __name__ == '__main__':
    unittest.main()
