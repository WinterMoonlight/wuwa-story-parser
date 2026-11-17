from copy import deepcopy
import unittest

from wuwa_story.reading import reading_text
from wuwa_story.reading_templates import format_templates, guide_text, update_selected_strings


class ReadingTemplateTests(unittest.TestCase):
    def test_input_arguments_use_labels_without_selecting_a_device(self):
        value = {'text': '按{0}并推动{1}', 'source_table': 'guidetips',
                 'format_argument_candidates': {'2': ['跳跃', '1#MoveForward'],
                                                '3': ['跳跃', '0#MoveForward']}}
        self.assertEqual(guide_text(value), '按【跳跃】并推动【前后移动】')
        self.assertEqual(guide_text({'text': '按{0}', 'source_table': 'guidetips'}), '按【操作键】')
        self.assertEqual(format_templates('奖励{0}'), '奖励【参数1】')

    def test_dynamic_names_use_values_or_descriptive_placeholders(self):
        token = '{Cus:Var,VarType=Global Key=main_team_name}'
        self.assertEqual(format_templates(token), '【队伍名称】')
        self.assertEqual(format_templates(token, {('global', 'main_team_name'): '呼啸浪潮'}), '呼啸浪潮')
        self.assertEqual(format_templates('{unknown}'), '{unknown}')

    def test_selected_write_updates_only_a_local_display_context(self):
        segment = {'source_actions': [], 'unverified_content': [{
            'trace': [{'kind': 'selected_route_constant_write',
                       'variable': {'Type': 'String', 'Source': 'Global', 'Keyword': 'main_team_name'},
                       'recorded_constant': '本次队名'}]}]}
        original = deepcopy(segment)
        values = {}
        update_selected_strings(values, segment)
        self.assertEqual(values, {('global', 'main_team_name'): '本次队名'})
        self.assertEqual(segment, original)
        self.assertEqual(format_templates('{Cus:Var,VarType=Global Key=main_team_name}'), '【队伍名称】')

    def test_real_team_name_follows_selected_choice_and_keeps_json(self):
        from wuwa_story.recap_backbone import export_task_backbone
        key = '剧情_2_4_七丘主线_上1_5_3:6'
        for index, name in [(0, '呼啸浪潮'), (1, '曜星狼')]:
            result = export_task_backbone(125000125, {key: index})
            original = deepcopy(result)
            text = reading_text(result)
            self.assertIn(name + ' 对战 伏尔甘矿业', text)
            self.assertNotIn('{Cus:', text)
            self.assertEqual(result, original)

    def test_unknown_rewrite_clears_value_and_self_scope_does_not_leak(self):
        values = {('global', 'name'): '旧名字'}
        segment = {'source_actions': [{'Name': 'SetVar', 'Params': {
            'VarLeft': {'Type': 'String', 'Source': 'Global', 'Keyword': 'name'}}}],
            'unverified_content': [{'trace': [{'kind': 'selected_route_constant_write',
                'variable': {'Type': 'String', 'Source': 'Self', 'Name': 'local'},
                'recorded_constant': '局部名字'}]}]}
        update_selected_strings(values, segment)
        self.assertEqual(values, {})


if __name__ == '__main__':
    unittest.main()
