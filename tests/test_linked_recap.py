from copy import deepcopy
import unittest

from wuwa_story.batch import Snapshot
from wuwa_story.database import embedded
from wuwa_story.export_task import Exporter
from wuwa_story.linked_recap import _candidate_anchor, _recap_only_tree, recover_linked_recap
from wuwa_story.mainline_reading import build_mainline_reading, mainline_reading_text
from wuwa_story.recap_backbone import export_task_backbone


class OverlaySource:
    def __init__(self, base, transform):
        self.base, self.transform = base, transform

    def rows(self, file, table):
        return self.transform(file, self.base.rows(file, table))


class LinkedRecapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Snapshot()
        cls.base = Exporter(source=cls.source, allow_incomplete=True).export(168850009)
        cls.quest = cls.base['source']['quest_definition']
        cls.nodes = cls.base['source']['task_nodes']
        cls.states = {r['StateKey']: r for r in cls.source.rows('db_flowState.db', 'flowstate')}
        cls.candidate = next(embedded(r['BinData'])[0][1]
            for r in cls.source.rows('db_QuestData.db', 'questdata') if r['QuestId'] == 168850014)
        cls.entries = next(embedded(r['BinData'])[0][1]
            for r in cls.source.rows('db_PlotHandBook.db', 'plothandbookconfig') if r['QuestId'] == 168850014)
        cls.keys = [f'剧情_3_7_心相迷宫&后日谈_3_{i}' for i in (10, 13, 11)]
        cls.placeholder_nodes = [embedded(r['BinData'])[0][1]
            for r in cls.source.rows('db_QuestNodeData.db', 'questnodedata') if r['Key'].startswith('168850014_')]

    def recover(self, source=None, nodes=None, states=None, choices=None):
        return recover_linked_recap(self.quest, self.nodes if nodes is None else nodes,
            self.base, self.states if states is None else states, source or self.source, choices)

    def test_real_successor_recap_orders_three_owned_flows_without_mutation(self):
        original = deepcopy(self.base)
        result = self.recover()
        self.assertEqual(result['candidates'], [168850014])
        section = result['sections'][0]
        self.assertEqual([s['state_key'] for s in section['segments']], self.keys)
        self.assertEqual([len(s['events']) for s in section['segments']], [30, 20, 26])
        self.assertEqual(section['proof']['anchor_node_id'], 6)
        self.assertEqual(section['insert_after_primary_events'], 51)
        self.assertFalse(section['runtime_verified'])
        self.assertFalse(section['proof']['runtime_node_order_verified'])
        self.assertEqual(self.base, original)

    def test_anchor_requires_exact_relation_tip_and_complete_owned_set(self):
        for mode in ('foreign_parent', 'wrong_type', 'chapter', 'tip', 'duplicate', 'partial', 'failure'):
            with self.subTest(mode=mode):
                c, entries, nodes = deepcopy(self.candidate), deepcopy(self.entries), deepcopy(self.nodes)
                if mode == 'foreign_parent': c['ProvideType']['Conditions'][0]['PreQuest'] = 123
                elif mode == 'wrong_type': c['Type'] = 1
                elif mode == 'chapter': c['ChapterId'] = -1
                elif mode == 'tip': entries[0]['TidTip'] = 'unknown'
                elif mode == 'duplicate': entries.append(deepcopy(entries[1]))
                elif mode == 'partial': entries.pop()
                else: next(n for n in nodes if n['Id'] == 7)['FailedCondition'] = {'Type': 'Unknown'}
                self.assertIsNone(_candidate_anchor(self.quest, c, entries, nodes, self.keys))

    def test_placeholder_tree_rejects_actual_logic_and_nonconstant_conditions(self):
        self.assertTrue(_recap_only_tree(self.placeholder_nodes))
        for mode in ('false', 'variable', 'action', 'root_condition', 'bad_shape'):
            with self.subTest(mode=mode):
                nodes = deepcopy(self.placeholder_nodes)
                step = next(n for n in nodes if n['Type'] == 'ChildQuest')
                compare = step['Condition']['Condition']['Conditions'][0]
                if mode == 'false': compare['Var2']['Value'] = 1
                elif mode == 'variable': compare['Var1'] = {'Type': 'Int', 'Source': 'Self', 'Name': 'unknown'}
                elif mode == 'action': step['EnterActions'] = [{'Name': 'PlayFlow'}]
                elif mode == 'root_condition': nodes[0]['Condition'] = {'Type': 'Unknown'}
                else: step['Condition']['Condition']['Conditions'] = None
                self.assertFalse(_recap_only_tree(nodes))

    def test_ambiguous_and_absent_recap_sources_do_not_create_order(self):
        for mode in ('duplicate_book', 'duplicate_quest', 'absent_quest'):
            def transform(file, rows):
                field = 'db_PlotHandBook.db' if mode == 'duplicate_book' else 'db_QuestData.db'
                if file != field:
                    return rows
                match = next(r for r in rows if r['QuestId'] == 168850014)
                return [r for r in rows if r['QuestId'] != 168850014] if mode == 'absent_quest' else rows + [match]
            with self.subTest(mode=mode):
                self.assertEqual(self.recover(OverlaySource(self.source, transform))['sections'], [])

    def test_missing_flow_and_conflicting_task_call_keep_original_unplaced(self):
        states = {k: v for k, v in self.states.items() if k != self.keys[0]}
        self.assertEqual(self.recover(states=states)['sections'], [])
        nodes = deepcopy(self.nodes)
        next(n for n in nodes if n['Id'] == 7)['FinishActions'].append({'Name': 'PlayFlow',
            'Params': {'FlowListName': '剧情_3_7_心相迷宫&后日谈', 'FlowId': 3, 'StateId': 9}})
        self.assertEqual(self.recover(nodes=nodes)['sections'], [])

    def test_explicit_choice_override_is_honored(self):
        default = self.recover()['sections'][0]['segments'][1]
        choice = default['route']['choices'][0]
        alternate = self.recover(choices={choice['choice_key']: 1})['sections'][0]['segments'][1]
        self.assertEqual(alternate['route']['choices'][0]['selected_index'], 1)
        self.assertNotEqual(default['events'], alternate['events'])

    def test_reading_projection_recovers_76_events_and_keeps_strict_scope(self):
        result = export_task_backbone(168850009)
        view = build_mainline_reading(result)
        self.assertEqual(view['retained_text_events'], 127)
        self.assertEqual(view['ordering_basis'], 'linked_recap_sections')
        self.assertEqual(view['status'], 'ordered_draft')
        self.assertFalse(view['runtime_verified'])
        self.assertEqual(len(result['events']), 51)
        self.assertEqual(result['validation']['reading_unplaced_flow_count'], 0)
        self.assertFalse(result['batch_coverage']['order']['selected_route_verified'])
        self.assertFalse(result['validation']['complete_for_supported_task_shape'])
        self.assertNotIn('normal_task_flows_unplaced', [g['kind'] for g in result['batch_coverage']['gaps']])
        text = mainline_reading_text(result)
        self.assertIn('数日后，玄方地界某处', text)
        self.assertEqual(text.count('数日后，玄方地界某处'), 1)


if __name__ == '__main__':
    unittest.main()
