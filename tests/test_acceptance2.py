import unittest
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.reading import reading_text


class GuidanceReadingTests(unittest.TestCase):
    def test_departure_is_followed_by_research_institute_not_guidance(self):
        result = export_task_backbone(139000027)
        sections = result['parallel_guidance']
        self.assertEqual(len(sections), 2)
        self.assertEqual(sum(len(s['events']) for s in sections), 4)
        keys = {s['state_key'] for s in sections}
        self.assertFalse(keys & {e.get('state_key') for e in result['events']})
        records = [r for r in result['batch_coverage']['records'] if r.get('reading_context')=='parallel_guidance']
        self.assertEqual(len(records),4)
        self.assertTrue(all(r['category']=='candidate_branch' and not r['order_verified'] for r in records))
        text = reading_text(result)
        label = text.index('【教学触发对白')
        for s in sections:
            for event in s['events']:
                self.assertIn(event['text'],text[label:])
                self.assertNotIn(event['text'],text[:label])


if __name__=='__main__':unittest.main()
