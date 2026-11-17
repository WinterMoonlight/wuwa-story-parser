import unittest
from types import SimpleNamespace
from unittest.mock import patch

from wuwa_story.dungeon_candidates import dungeon_candidates


class DungeonCandidateTests(unittest.TestCase):
    def test_no_transition_does_not_scan(self):
        self.assertEqual(dungeon_candidates([], None), ([], [], []))

    def test_ambiguous_dungeon_rejected(self):
        action = {'Name': 'TeleportDungeon', 'Params': {'DungeonId': 5}}
        source = SimpleNamespace(rows=lambda db, table: [{'Id': 5}, {'Id': 5}]
                                 if table == 'instancedungeon' else [])
        links, gaps, audits = dungeon_candidates([{'Id': 1, 'EnterActions': [action]}], source)
        self.assertFalse(links)
        self.assertEqual(gaps[0]['reason'], 'missing_or_ambiguous_dungeon')

    def test_real_research_dungeon_has_eighteen_candidate_lines(self):
        from wuwa_story.batch import Snapshot
        from wuwa_story.database import embedded, texts
        from wuwa_story.export_task import flow_actions, walk
        source = Snapshot()
        nodes = [embedded(r['BinData'])[0][1]
                 for r in source.rows('db_QuestNodeData.db', 'questnodedata')
                 if r['Key'].startswith('139000027_')]
        links, gaps, audits = dungeon_candidates(nodes, source)
        research = [link for link in links if link['dungeon_link']['dungeon_id'] == 1505]
        self.assertEqual({link['levelplay_id'] for link in research}, {610800000})
        self.assertEqual(len({link['state_key'] for link in research}), 9)
        self.assertTrue(all(not link['order_verified'] for link in research))
        states = {r['StateKey']: r for r in source.rows('db_flowState.db', 'flowstate')}
        ids = set()
        for key in {link['state_key'] for link in research}:
            actions, _ = flow_actions(states[key]['BinData'])
            ids.update(item['TidTalk'] for item in walk(actions) if item.get('TidTalk'))
        self.assertEqual(len(ids), 18)
        self.assertTrue(all(key in texts for key in ids))
        self.assertTrue(any(link.get('reference_kind') == 'flow_completion_condition' for link in research))


if __name__ == '__main__':
    unittest.main()
