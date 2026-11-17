import unittest
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.reading import reading_text


class DungeonReturnReadingTests(unittest.TestCase):
    def test_completion_dialogue_and_transition_have_separate_scopes(self):
        result=export_task_backbone(139000027)
        sections=result['dungeon_return_sections']
        before=next(s for s in sections if s['scope']=='before_explicit_dungeon_completion')
        transition=next(s for s in sections if s['scope']=='success_transition')
        self.assertEqual(before['placement'],'body')
        self.assertEqual(len(before['events']),4)
        self.assertEqual(transition['placement'],'supplement')
        self.assertEqual(len(transition['events']),1)
        self.assertEqual(before['entry_index'],44)
        text=reading_text(result)
        last=before['events'][-1]['text']
        self.assertLess(text.index(last),text.index('更具体一点呢'))
        self.assertIn('你将方才发生的事情告诉了秧秧与白芷',text)
        self.assertIn('相对顺序待核查',text)
        self.assertFalse(before['proof']['runtime_verified'])
        keys={key for s in sections for key in s['state_keys']}
        candidates=[r for r in result['batch_coverage']['records'] if r.get('origin')in keys]
        self.assertFalse(candidates)


if __name__=='__main__':unittest.main()
