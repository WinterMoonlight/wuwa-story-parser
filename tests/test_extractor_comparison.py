import unittest
from wuwa_story.extractor_comparison import compare_extractions


class ComparisonTests(unittest.TestCase):
    def test_same_text_in_another_state_is_not_covered(self):
        ours={'events':[{'state_key':'a','text_id':'t'}], 'batch_coverage':{'records':[]}}
        report=compare_extractions(ours,{'all_lines':[{'state_key':'b','text_key':'t'}]})
        self.assertEqual(report['shared'],0)
        self.assertEqual(report['reference_only_unique'],1)

    def test_options_and_duplicate_occurrences_count_separately(self):
        ours={'events':[], 'batch_coverage':{'records':[{'origin':'s','text_id':'a'}]}}
        line={'state_key':'s','text_key':'a','options':[{'text_key':'b'}]}
        report=compare_extractions(ours,{'all_lines':[line,line]})
        self.assertEqual(report['reference_unique'],2)
        self.assertEqual(report['reference_only_unique'],1)
        self.assertEqual(len(report['reference_only']),2)

    def test_recap_order_reverse_and_repeated_state_unresolved(self):
        ours={'events':[], 'batch_coverage':{'records':[]},'recap_backbone':{'segments':[
            {'state_key':k,'events':[]} for k in ['b','a','c','c']]}}
        report=compare_extractions(ours,{'all_lines':[{'state_key':k,'text_key':'t'} for k in ['a','b','c']]})
        self.assertEqual([x['status'] for x in report['adjacent_recap_order_checks']],['reversed','unresolved','unresolved'])


if __name__=='__main__':unittest.main()
