import unittest

from wuwa_story.dependency_positions import adjacent_sync_dependencies, dependency_positions


def flow(state, **extra):
    return {'Name': 'PlayFlow', 'Params': {'FlowListName': 'f', 'FlowId': 1, 'StateId': state}, **extra}


class DependencyPositionsTests(unittest.TestCase):
    def test_unique_reversal_and_forward_order(self):
        edges = adjacent_sync_dependencies([{'Type': 'ChildQuest', 'Id': 5, 'FinishActions': [flow(1), flow(2)]}])
        self.assertEqual(len(edges), 1)
        self.assertEqual(len(dependency_positions(edges, ['f_1_2', 'f_1_1'])['conflicts']), 1)
        forward = dependency_positions(edges, ['f_1_1', 'f_1_2'])
        self.assertEqual(len(forward['consistent']), 1)
        self.assertFalse(forward['conflicts'])
        self.assertFalse(edges[0]['runtime_executed'])

    def test_repeated_or_absent_occurrences_never_claim_order(self):
        edge = {'from_state': 'a', 'to_state': 'b'}
        for ordered, expected in ((['b', 'a', 'b'], ([1], [0, 2])), (['a'], ([0], []))):
            result = dependency_positions([edge], ordered)
            self.assertFalse(result['conflicts'])
            self.assertFalse(result['consistent'])
            self.assertEqual(result['unresolved'][0]['from_positions'], expected[0])
            self.assertEqual(result['unresolved'][0]['to_positions'], expected[1])
        result = dependency_positions([{'from_state': 'a', 'to_state': 'a'}], ['a'])
        self.assertEqual(result['unresolved'][0]['reason'], 'same_reference_does_not_identify_two_distinct_calls')

    def test_async_unknown_fields_and_nonadjacent_calls_are_not_edges(self):
        for update in ({'Async': True}, {'Async': 0}, {'Async': None}, {'Condition': {}}, {'Callback': []}):
            for index in (0, 1):
                actions = [flow(1), flow(2)]
                actions[index].update(update)
                self.assertEqual(adjacent_sync_dependencies([{'Type': 'ChildQuest', 'FinishActions': actions}]), [])
        actions = [flow(1), {'Name': 'Wait', 'Params': {'Time': 1}}, flow(2)]
        self.assertEqual(adjacent_sync_dependencies([{'Type': 'ChildQuest', 'FinishActions': actions}]), [])
        first = flow(1); first['Params']['Condition'] = {}
        self.assertEqual(adjacent_sync_dependencies([{'Type': 'ChildQuest', 'FinishActions': [first, flow(2)]}]), [])
        self.assertEqual(adjacent_sync_dependencies([{'Type': 'Sequence', 'FinishActions': [flow(1), flow(2)]}]), [])

    def test_explicit_false_and_metadata_are_supported(self):
        actions = [flow(1, Async=False, ActionId=7, ActionGuid='x'), flow(2)]
        edges = adjacent_sync_dependencies([{'Id': 9, 'Type': 'ChildQuest', 'FinishActions': actions}])
        self.assertEqual(edges[0]['from_finish_action_index'], 0)
        self.assertEqual(edges[0]['finish_action_index'], 1)
        self.assertEqual(edges[0]['source_actions'], actions)

    def test_real_repeated_flow_in_bencehoucanxing_keeps_both_positions(self):
        from wuwa_story.database import rows, embedded
        from wuwa_story.export_task import flow_key
        node = next(embedded(r['BinData'])[0][1] for r in rows('db_QuestNodeData.db', 'questnodedata')
                    if r['Key'] == '139000030_116')
        book = next(r for r in rows('db_PlotHandBook.db', 'plothandbookconfig') if r['QuestId'] == 139000030)
        entries = next(v for _, v in embedded(book['BinData']) if isinstance(v, list))
        ordered = [flow_key(e['Flow']) for e in entries if e.get('Flow', {}).get('FlowListName')]
        edges = adjacent_sync_dependencies([node])
        result = dependency_positions(edges, ordered)
        self.assertFalse(result['conflicts'])
        repeated = next(e for e in result['unresolved'] if e['to_state'].endswith('_1_26'))
        self.assertEqual(repeated['from_positions'], [17])
        self.assertEqual(repeated['to_positions'], [10, 18])
        self.assertEqual(repeated['reason'], 'repeated_recap_occurrences_need_callsite_mapping')


if __name__ == '__main__':
    unittest.main()
