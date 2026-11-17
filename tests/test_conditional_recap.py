import unittest
from unittest.mock import patch
from wuwa_story.export_task import Exporter
from wuwa_story.variables import VariableEnvironment
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.reading import reading_text


class ConditionalRecapTests(unittest.TestCase):
    def test_setvar_requires_explicit_environment_and_only_selected_option_runs(self):
        def assign(value):
            return {'Name': 'SetVar', 'Params': {'VarLeft': {'Type': 'Boolean', 'Source': 'Self', 'Name': 'side'},
                    'VarRight': {'Type': 'Boolean', 'Source': 'Constant', 'Value': value}}}
        items = [{'Type': 'Talk', 'Id': 1, 'WhoId': 1, 'TidTalk': 'ask', 'Options': [
            {'TidTalkOption': 'left', 'Actions': [assign(False)]},
            {'TidTalkOption': 'right', 'Actions': [assign(True)]}]}]
        env = VariableEnvironment('test')
        p = Exporter(allow_incomplete=True, variable_environment=env); p.state_key = 'flow'
        with patch('wuwa_story.export_task.texts', {'ask': '?', 'left': 'L', 'right': 'R'}):
            p.action({'Name': 'ShowTalk', 'Params': {'TalkItems': items}})
        self.assertEqual(len(env.trace), 1)
        self.assertIs(env.snapshot()[0]['value'], False)
        p = Exporter(allow_incomplete=True); p.state_key = 'flow'
        with self.assertRaises(ValueError): p.action(assign(False))
        p = Exporter(variable_environment=env); p.state_key = 'flow'
        with self.assertRaises(ValueError): p.action(assign(False))

    def test_real_left_right_keep_occurrences_and_selected_dialogue_consistent(self):
        prefix = '剧情_2_5_隐海试验场_声骸培养场'
        for index, excluded, included in [(0, {12, 14}, {8}), (1, {8}, {12, 14})]:
            result = export_task_backbone(147000002, {prefix+'_1_2:11': index})
            b = result['recap_backbone']; proof = b['conditional_selections'][0]
            self.assertEqual(proof['selected_slot'], index)
            self.assertEqual(set(proof['excluded_entry_indices']), excluded)
            self.assertFalse(proof['runtime_route_verified'])
            segments = {s['entry_index']: s for s in b['segments']}
            self.assertEqual(next(c for c in segments[6]['route']['choices'] if c['choice_key'] == prefix+'_1_2:11')['selected_index'], index)
            self.assertIs(segments[6]['variable_trace'][0]['after'], bool(index))
            for i in included: self.assertEqual(segments[i]['status'], 'parsed')
            for i in excluded:
                self.assertEqual(segments[i]['events'], [])
                self.assertIn('unselected_original', segments[i])
            keys = [s['state_key'] for s in b['segments'] if s['status']=='parsed']
            self.assertEqual(keys.count(prefix+'_1_17'), 1)
            self.assertFalse(result['batch_coverage']['reading_acceptance']['accepted'])
            txt = reading_text(result)
            self.assertIn('该选择值未被其他交互覆盖', txt)
            main = txt.split('【附录：')[0]
            right_text = segments[12].get('unselected_original', segments[12])['events'][0]['text']
            if index == 0: self.assertNotIn(right_text, main)
            else: self.assertIn(right_text, main)


    def test_known_overwrite_and_async_writer_reject_projection_without_losing_source(self):
        from copy import deepcopy
        from wuwa_story.batch import Snapshot
        from wuwa_story.database import embedded
        from wuwa_story.export_task import walk
        from wuwa_story.recap_backbone import build_backbone
        from wuwa_story.conditional_recap import project_conditional_recap
        source = Snapshot(); qid = 147000002
        nodes = [embedded(r['BinData'])[0][1] for r in source.rows('db_QuestNodeData.db', 'questnodedata')
                 if r['Key'].startswith(str(qid) + '_')]
        books = [r for r in source.rows('db_PlotHandBook.db', 'plothandbookconfig') if r['QuestId'] == qid]
        states = {r['StateKey']: r for r in source.rows('db_flowState.db', 'flowstate')}
        original = build_backbone(qid, books, states, source)
        for mutation in ('overwrite', 'async'):
            b = deepcopy(original); ns = deepcopy(nodes)
            writer = next(s for s in b['segments'] if s['entry_index'] == 6)
            if mutation == 'overwrite':
                assignment = deepcopy(next(o for o in walk(writer['source_actions']) if o.get('Name') == 'SetVar'))
                assignment['Params']['VarRight']['Value'] = True
                next(n for n in ns if n['Id'] == 22)['FinishActions'].append(assignment)
            else:
                next(a for a in writer['source_actions'] if a['Name'] == 'ShowTalk')['Async'] = True
            before = deepcopy(b['segments'])
            self.assertEqual(project_conditional_recap(b, ns, source), [])
            self.assertEqual(b['segments'], before)
            self.assertFalse(b['conditional_rejections'][0]['guard']['allowed'])
            self.assertFalse(any(s['status'] == 'excluded_branch' for s in b['segments']))
