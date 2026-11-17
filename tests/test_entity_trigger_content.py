import unittest
from types import SimpleNamespace
from unittest.mock import patch

from wuwa_story.entity_trigger_content import entity_trigger_content


class EntityTriggerTests(unittest.TestCase):
    def row(self, map_id=8):
        return {'Id': 1, 'MapId': map_id, 'EntityId': 20, 'BinData': b'source'}

    def call(self, name='PlayFlow', state=3):
        return {'Name': name, 'Params': {'FlowListName': 'flow', 'FlowId': 2, 'StateId': state}, 'Async': True}

    def extract(self, config, records=None):
        source = SimpleNamespace(rows=lambda *args: [self.row()] if records is None else records)
        with patch('wuwa_story.entity_trigger_content.embedded', return_value=[(1, config), (2, config)]):
            return entity_trigger_content({'Children': ['e_8_20']}, source)

    def test_explicit_calls_keep_context_and_occurrences(self):
        cfg = {'TriggerComponent': {'Condition': {'Unknown': True}, 'Actions': [self.call()],
                                   'ExitConfig': {'Actions': [self.call()]}},
               'ClientTriggerComponent': {'OnTriggerEnter': {'Actions': [self.call()]},
                                          'OnTriggerExit': {'Actions': [self.call()]}},
               'EntityStateComponent': {'StateChangeBehaviors': [
                   {'State': 'completed', 'Action': [self.call()]}]}}
        links, gaps = self.extract(cfg)
        self.assertFalse(gaps)
        self.assertEqual(len(links), 5)
        self.assertEqual(len({tuple(x['source_path']) for x in links}), 5)
        self.assertTrue(all(not x['order_verified'] and not x['runtime_trigger_verified'] and
                            not x['mandatory_verified'] for x in links))
        self.assertEqual(links[0]['source_component']['Condition'], {'Unknown': True})
        self.assertEqual(links[-1]['source_component']['StateChangeBehaviors'][0]['State'], 'completed')
        self.assertEqual(links[0]['equivalent_json_fields'], [1, 2])

    def test_preload_reference_or_arbitrary_nested_object_is_not_invocation(self):
        cfg = {'TriggerComponent': {'Actions': [self.call('Preload'), self.call('RemovePreloadResource')],
                                    'Arbitrary': {'Actions': [self.call()]}},
               'OtherComponent': {'Actions': [self.call()]}}
        self.assertEqual(self.extract(cfg), ([], []))

    def test_invalid_ids_not_coerced(self):
        links, gaps = self.extract({'TriggerComponent': {'Actions': [self.call(state=True)]}})
        self.assertFalse(links)
        self.assertEqual(gaps[0]['reason'], 'malformed_flow_reference')

    def test_ownership_requires_exact_map_and_unique_row(self):
        for records in ([self.row(9)], [self.row(), self.row()]):
            links, gaps = self.extract({}, records)
            self.assertFalse(links)
            self.assertEqual(gaps[0]['reason'], 'missing_or_ambiguous_entity_row')
        self.assertEqual(entity_trigger_content({'Reference': ['e_8_20']}, None), ([], []))

    def test_disagreeing_fields_rejected(self):
        source = SimpleNamespace(rows=lambda *args: [self.row()])
        with patch('wuwa_story.entity_trigger_content.embedded', return_value=[(1, {}), (2, {'x': 1})]):
            links, gaps = entity_trigger_content({'Children': ['e_8_20']}, source)
        self.assertFalse(links)
        self.assertEqual(gaps[0]['reason'], 'ambiguous_entity_config')

    def test_real_voyaging_star_three_async_triggers(self):
        from wuwa_story.database import rows, embedded
        q = next(q for r in rows('db_QuestData.db', 'questdata') for _, q in embedded(r['BinData'])
                 if isinstance(q, dict) and q.get('Id') == 690000001)
        links, gaps = entity_trigger_content(q, SimpleNamespace(rows=rows))
        self.assertFalse(gaps)
        self.assertEqual({x['state_key'] for x in links}, {
            '剧情_3_1_拉海洛主线_上半_1_20_1', '剧情_3_1_拉海洛主线_上半_1_25_1',
            '剧情_3_1_拉海洛主线_上半_1_69_1'})
        self.assertTrue(all(x['source_path'] == ['TriggerComponent', 'Actions', 0] for x in links))
        self.assertTrue(all(x['invocation_async'] and not x['order_verified'] for x in links))


if __name__ == '__main__':
    unittest.main()
