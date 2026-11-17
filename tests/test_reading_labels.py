from copy import deepcopy
import unittest

from wuwa_story.reading import reading_exclusion_reason, reading_text
from wuwa_story.recap_backbone import export_task_backbone


class ReadingLabelTests(unittest.TestCase):
    def sample(self):
        return {'title': '示例任务',
                'task_ui_texts': [
                    {'source_path': ['TidTip'], 'raw_text': '前往教堂'},
                    {'source_path': ['OccupationConfig', 'TidDesc'], 'raw_text': '角色被占用'},
                    {'source_path': ['UIConfig', 'TidContent'], 'raw_text': '一封旧信的内容'}],
                'batch_coverage': {'status': 'inventory_only',
                    'order': {'selected_route_verified': False}, 'gaps': [],
                    'records': [
                        {'category': 'unverified', 'pointer': '/task_ui_texts/0', 'text': '前往教堂'},
                        {'category': 'unverified', 'pointer': '/task_ui_texts/1', 'text': '角色被占用'},
                        {'category': 'unverified', 'pointer': '/task_ui_texts/2', 'text': '一封旧信的内容'},
                        {'category': 'candidate_branch', 'kind': 'dialogue', 'display_name': '秧秧',
                         'origin': 'dialogue', 'text': '前往教堂'},
                        {'category': 'candidate_branch', 'kind': 'choice', 'display_name': '漂泊者',
                         'origin': 'dialogue', 'text': '前往教堂'}]}}

    def test_source_fields_hide_labels_and_preserve_same_wording_in_dialogue(self):
        result = self.sample()
        original = deepcopy(result)
        text = reading_text(result)
        self.assertIn('秧秧：前往教堂', text)
        self.assertIn('漂泊者【选择】：前往教堂', text)
        self.assertEqual(text.count('前往教堂'), 2)
        self.assertNotIn('角色被占用', text)
        self.assertIn('一封旧信的内容', text)
        self.assertEqual(result, original)

    def test_system_buttons_hidden_and_unknown_options_preserved(self):
        result = self.sample()
        result['batch_coverage']['records'] = [
            {'category': 'candidate_branch', 'kind': 'system_option',
             'display_name': '系统选项', 'origin': 'button', 'text': '进入礼堂'},
            {'category': 'candidate_branch', 'kind': 'unknown_option',
             'origin': 'unknown', 'text': '尚未识别的选择'}]
        text = reading_text(result)
        self.assertNotIn('进入礼堂', text)
        self.assertIn('尚未识别的选择', text)

    def test_only_labels_leave_no_empty_supplement_headers(self):
        result = self.sample()
        result['batch_coverage']['records'] = result['batch_coverage']['records'][:2]
        text = reading_text(result)
        self.assertNotIn('【补充片段】', text)
        self.assertNotIn('【待核验的对白、小游戏及界面材料】', text)
        self.assertIn('当前未提取到可阅读正文', text)

    def test_legacy_records_filter_without_new_metadata(self):
        result = self.sample()
        record = result['batch_coverage']['records'][0]
        self.assertEqual(reading_exclusion_reason(result, record), 'task_objective_label')
        record['reading_exclusion_reason'] = 'task_objective_label'
        annotated = reading_text(result)
        del record['reading_exclusion_reason']
        self.assertEqual(annotated, reading_text(result))
        self.assertIsNone(reading_exclusion_reason(result, {'pointer': '/task_ui_texts/900'}))

    def test_real_voyage_screenshot_dialogue_preserved(self):
        result = export_task_backbone(690000001)
        original = deepcopy(result)
        text = reading_text(result)
        self.assertNotIn('前往空间站入口', text)
        self.assertNotIn('进入礼堂', text)
        for phrase in ('欢迎来到天槎空间站', '刚才获得的权限', '那团流动的球形液体'):
            self.assertIn(phrase, text)
        excluded = [r for r in result['batch_coverage']['records'] if r.get('reading_exclusion_reason')]
        self.assertTrue(excluded)
        self.assertEqual(len(excluded), result['batch_coverage']['source_counts']['reading_excluded_labels'])
        self.assertTrue(any(v.get('raw_text') == '进入礼堂' for v in result['task_ui_texts']))
        self.assertEqual(result, original)


if __name__ == '__main__':
    unittest.main()
