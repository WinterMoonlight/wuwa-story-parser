import unittest
from wuwa_story.qte_evidence import inspect_qte


class QteEvidenceTests(unittest.TestCase):
    def test_empty_missing_and_present_are_distinct(self):
        items = [{'Type': 'QTE', 'Id': i, 'QteId': 10+i, 'TidTalk': str(i)} for i in range(3)]
        r = inspect_qte({'TalkItems': items, 'TalkSequence': [[0, 1, 2]]}, {'0': '', '2': 'text'})
        self.assertEqual([i['text_status'] for i in r['items']], ['empty', 'missing', 'present'])
        self.assertTrue(r['explicit_linear_sequence'])
        self.assertFalse(r['configured_order_is_runtime_route'])
        self.assertTrue(all(i['outcome_mapping_status'] == 'unresolved' for i in r['items']))

    def test_duplicate_or_different_sequence_does_not_prove_order(self):
        for sequence in ([[1, 0]], [[0], [1]], None):
            r = inspect_qte({'TalkItems': [{'Type': 'QTE', 'Id': 0}, {'Type': 'QTE', 'Id': 1}],
                             'TalkSequence': sequence}, {})
            self.assertFalse(r['explicit_linear_sequence'])
            self.assertTrue(all(i['configured_index'] is None for i in r['items']))
