import unittest

from wuwa_story.reading_markup import reading_markup


class ReadingMarkupTests(unittest.TestCase):
    def test_known_color_styles_preserve_wording_and_newlines(self):
        source = '受到<color=Highlight>天空海</color>影响\n<color=#8c7e51>钩索</color><color=#FFFFFFFF>工具</color>'
        self.assertEqual(reading_markup(source), '受到天空海影响\n钩索工具')

    def test_annotations_preserve_display_text_and_definition(self):
        source = '携带<ano=终端><color=Highlight>葫芦</color></ano>，前往<ano=数据库>类书</ano>。'
        expected = '携带葫芦〔终端〕，前往类书〔数据库〕。'
        self.assertEqual(reading_markup(source), expected)
        self.assertEqual(reading_markup(expected), expected)

    def test_all_presentation_tags_are_removed(self):
        for source in ('<color=Unknown>x</color>', '<color=#123>x</color>',
                       '<color=Highlight>x', '<ano=术语>x',
                       '<color=Highlight><foo>x</color></foo>', '<foo>x</foo>',
                       '<TE href="850166">x</TE>', '<b><i><s>x</s></i></b>',
                       '<size=28>x</size><alignright/>'):
            with self.subTest(source=source):
                self.assertEqual(reading_markup(source), 'x')

    def test_attributes_line_breaks_and_comparisons(self):
        source = '<te href="a>b">术语</te><BR/>下行<br>末行\na < b > c，1 < 2'
        expected = '术语\n下行\n末行\na < b > c，1 < 2'
        self.assertEqual(reading_markup(source), expected)
        self.assertEqual(reading_markup(expected), expected)

    def test_runtime_placeholders_and_gender_tokens_are_not_guessed(self):
        source = '消灭残象（{q_count}/2）按{0}与{1}，{PlayerName}{MALE=哥;FEMALE=姐}'
        self.assertEqual(reading_markup(source), source)

    def test_display_function_does_not_modify_source(self):
        source = {'raw_text': '<ano=声之领域>索诺拉</ano>', 'text': '<ano=声之领域>索诺拉</ano>'}
        self.assertEqual(reading_markup(source['text']), '索诺拉〔声之领域〕')
        self.assertEqual(source['raw_text'], '<ano=声之领域>索诺拉</ano>')
        self.assertEqual(source['text'], source['raw_text'])


if __name__ == '__main__':
    unittest.main()
