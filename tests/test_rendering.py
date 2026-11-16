import unittest
from wuwa_story.rendering import render_text, render_result


class RenderingTests(unittest.TestCase):
    def test_female_branch_is_not_pronoun_guessing(self):
        self.assertEqual(render_text('{PlayerName}，{Male=哥哥;Female=姐姐}，{TA}来了。'),
                         '漂泊者，姐姐，她来了。')
        self.assertEqual(render_text('{Male=她;Female=他}'), '他')
        self.assertEqual(render_text('{FEMALE=女士;MALE=先生}'), '女士')
        self.assertEqual(render_text('{Male=哥哥;Female={PlayerName}}'), '漂泊者')
        self.assertEqual(render_text('他与她：{0}、{未知}'), '他与她：{0}、{未知}')

    def test_rendered_outputs_preserve_source(self):
        raw = '{PlayerName}{Male=哥哥;Female=姐姐}'
        result = {'title': raw, 'route': {'choices': [{'options': [{'text': raw}]}]},
                  'events': [{'raw_text': raw, 'display_name': '{PlayerName}'}]}
        render_result(result)
        self.assertEqual(result['events'][0]['text'], '漂泊者姐姐')
        self.assertEqual(result['events'][0]['raw_text'], raw)
        self.assertEqual(result['events'][0]['display_name'], '漂泊者')
        self.assertEqual(result['route']['choices'][0]['options'][0]['text'], '漂泊者姐姐')
