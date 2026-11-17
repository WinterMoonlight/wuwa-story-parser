import copy
import unittest
from unittest.mock import patch
from wuwa_story.constant_writes import constant_write_shape, constant_write_recorder


def assignment(kind='Boolean', value=True, source='Global'):
    return {'Name': 'SetVar', 'Params': {
        'VarLeft': {'Type': kind, 'Source': source,
                    'Keyword' if source == 'Global' else 'Name': 'x'},
        'VarRight': {'Type': kind, 'Source': 'Constant', 'Value': value}}}


class ConstantWriteTests(unittest.TestCase):
    def test_real_selected_global_constants(self):
        from wuwa_story.batch import Snapshot
        from wuwa_story.export_task import Exporter, flow_actions
        source = Snapshot()
        states = {r['StateKey']: r['BinData'] for r in source.rows('db_flowState.db', 'flowstate')}
        cases = [
            ('剧情_2_4_七丘主线_上1_5_3', 6, 2, ['MAIN_RYAM_16_9']),
            ('剧情_2_5_隐海试验场_坟场_1_1', 23, 1, [False]),
            ('剧情_3_5_玄方城_决战_4_3_29', 2, 1, [1]),
            ('剧情_3_2_拉海洛主线_下半_12_1', 3, 0, [True, True]),
        ]
        for key, talk_id, index, expected in cases:
            with self.subTest(state_key=key):
                actions, _ = flow_actions(states[key])
                recorder = constant_write_recorder(actions, key)
                self.assertIsNotNone(recorder)
                parser = Exporter(source=source, allow_incomplete=True,
                    choices={key + ':' + str(talk_id): index}, variable_environment=recorder)
                parser.state_key = key
                self.assertIsNone(parser.actions(actions))
                self.assertEqual([r['recorded_constant'] for r in recorder.trace], expected)
                self.assertTrue(parser.events)
                self.assertTrue(all(r['runtime_executed'] is False for r in recorder.trace))

    def test_exact_shapes(self):
        for kind, good, bad in [('Boolean', True, 1), ('Int', 3, True), ('String', 'x', 3)]:
            for source in ('Self', 'Global'):
                self.assertTrue(constant_write_shape(assignment(kind, good, source)))
                self.assertFalse(constant_write_shape(assignment(kind, bad, source)))
        for extra in [{'Async': True}, {'Timeout': 1}, {'OnFinish': []}]:
            self.assertFalse(constant_write_shape(dict(assignment(), **extra)))
        for bad in [None, [], {}, {'Name': 'SetVar', 'Params': None},
                    assignment('Int', 2**31), assignment('Float', 1.0)]:
            self.assertFalse(constant_write_shape(bad))
        bad = assignment(); bad['Params']['VarLeft']['Name'] = 'also_named'
        self.assertFalse(constant_write_shape(bad))

    def test_full_tree_rejections_and_template_boundary(self):
        a = assignment()
        for extra in [{'Name': 'FinishState'}, {'Name': 'ChangeState'}, {'Name': 'PlayFlow'},
                      {'PreCondition': {}}, {'Var1': {}}, {'Source': 'Global'}]:
            self.assertIsNone(constant_write_recorder([a, {'Options': [extra]}], 'test'))
        bad = assignment(); bad['Params']['VarRight']['Source'] = 'Global'
        self.assertIsNone(constant_write_recorder([a, bad], 'test'))
        self.assertIsNone(constant_write_recorder([], 'test'))
        item = {'TidTalk': 'line'}
        with patch('wuwa_story.constant_writes.texts', {'line': '{PlayerName}，你好'}):
            self.assertIsNotNone(constant_write_recorder([a, item], 'test'))
        for text in ('{main_team_name}', '%s', '{unknown}'):
            with patch('wuwa_story.constant_writes.texts', {'line': text}):
                self.assertIsNone(constant_write_recorder([a, item], 'test'))

    def test_record_only_and_selected_assignments(self):
        a, b = assignment(), assignment(value=False)
        recorder = constant_write_recorder([a, b], 'occurrence:1')
        recorder.assign(a)
        self.assertEqual(len(recorder.trace), 1)
        self.assertIs(recorder.trace[0]['recorded_constant'], True)
        self.assertFalse(recorder.trace[0]['global_state_established'])
        self.assertFalse(hasattr(recorder, 'read'))
        self.assertFalse(hasattr(recorder, 'evaluate'))
        other = constant_write_recorder([a, b], 'occurrence:2')
        self.assertEqual(other.trace, [])
        snapshot = recorder.snapshot(); snapshot[0]['variable']['Keyword'] = 'changed'
        self.assertEqual(recorder.trace[0]['variable']['Keyword'], 'x')
