import copy
import unittest

from wuwa_story.mainline_reading import build_mainline_reading, mainline_reading_text


class MainlineReadingTests(unittest.TestCase):
    def document(self, events):
        return {'title': '测试任务', 'events': events, 'validation': {}}

    def test_selected_story_and_choices_preserve_order_and_source(self):
        events = [
            {'kind': 'dialogue', 'display_name': '甲', 'text': '比赛开始'},
            {'kind': 'choice', 'text': '参加比赛'},
            {'kind': 'qte_reference', 'text': '内部参数'},
            {'kind': 'dialogue', 'display_name': '乙', 'text': '比赛结束'},
        ]
        result = self.document(events)
        result['external_content'] = [{'gameplay': {'reigns_id': 1},
                                       'texts': [{'text': '失败结局'}]}]
        before = copy.deepcopy(result)
        view = build_mainline_reading(result)
        text = mainline_reading_text({**result, 'mainline_reading': view})
        self.assertEqual(result, before)
        self.assertLess(text.index('比赛开始'), text.index('参加比赛'))
        self.assertLess(text.index('参加比赛'), text.index('比赛结束'))
        self.assertIn('互动操作过程略', text)
        self.assertNotIn('失败结局', text)
        self.assertNotIn('获胜', text)
        self.assertEqual(view['blocks'][0]['parts'][-1]['source_pointers'], ['/events/3'])
        self.assertEqual(view['omitted_gameplay_groups'], 1)

    def test_recap_gap_and_excluded_branch(self):
        result = self.document([])
        result['recap_backbone'] = {'segments': [
            {'entry_index': 0, 'status': 'parsed', 'events': [
                {'kind': 'dialogue', 'text': '前段', 'display_name': '甲'}]},
            {'entry_index': 1, 'status': 'blocked', 'events': [{'kind': 'recap_gap'}]},
            {'entry_index': 2, 'status': 'excluded_branch', 'events': [
                {'kind': 'dialogue', 'text': '未选择路线', 'display_name': '甲'}]},
            {'entry_index': 3, 'status': 'parsed', 'events': [
                {'kind': 'dialogue', 'text': '后段', 'display_name': '甲'}]},
        ]}
        text = mainline_reading_text(result)
        self.assertLess(text.index('前段'), text.index('未解析过程'))
        self.assertLess(text.index('未解析过程'), text.index('后段'))
        self.assertNotIn('未选择路线', text)
        self.assertEqual(build_mainline_reading(result)['status'], 'ordered_draft_with_gaps')

    def test_inventory_never_becomes_ordered_body(self):
        result = self.document([])
        result['batch_coverage'] = {'status': 'inventory_only', 'records': [
            {'category': 'unverified', 'pointer': '/external_content/0', 'text': '候选内容'}]}
        result['external_content'] = [{'text': '候选内容'}]
        self.assertEqual(build_mainline_reading(result)['status'], 'no_ordered_body')
        self.assertNotIn('候选内容', mainline_reading_text(result))

    def test_local_segments_warn_about_global_order(self):
        result = self.document([])
        result['task_local_sequences'] = [{'segments': [
            {'events': [{'kind': 'dialogue', 'text': '局部内容'}]}]}]
        self.assertEqual(build_mainline_reading(result)['status'], 'local_fragments_only')
        self.assertIn('片段间的先后尚未确定', mainline_reading_text(result))

    def test_information_and_screen_text_are_retained(self):
        result = self.document([
            {'kind': 'information_board', 'display_name': '资料', 'text': '资料正文'},
            {'kind': 'center_text', 'display_name': '画面文字', 'text': '第二天'},
        ])
        text = mainline_reading_text(result)
        self.assertIn('资料正文', text)
        self.assertIn('第二天', text)


if __name__ == '__main__':
    unittest.main()
