import unittest
from wuwa_story.reigns_rules import compare, audit_rules
from wuwa_story.paths import DATABASE_DIR


class RuleAuditTests(unittest.TestCase):
    def test_comparisons_and_unknown_values(self):
        self.assertTrue(compare(100, 'Ge', 100))
        self.assertFalse(compare(100, 'Gt', 100))
        self.assertTrue(compare(0, 'Le', 0))
        self.assertIsNone(compare(None, 'Eq', 1))
        with self.assertRaises(ValueError):
            compare(1, 'Unknown', 1)

    def test_does_not_assign_combination_enum_or_ignore_buff(self):
        result = audit_rules([{'Name': 'ReignsAddBuff', 'Params': {'BuffId': 1}}],
            [{'IsSuccess': True, 'Conditions': {'ConditionType': 0, 'Conditions': [
                {'PropertyId': 1, 'Compare': 'Ge', 'Target': 50},
                {'PropertyId': 2, 'Compare': 'Ge', 'Target': 50}]}, 'CardId': 1, 'CardIds': [2]}],
            [{'Id': 1, 'BaseValue': 100}, {'Id': 2, 'BaseValue': 0}])
        self.assertTrue(result['ending_probes'][0]['initial_if_any'])
        self.assertFalse(result['ending_probes'][0]['initial_if_all'])
        self.assertFalse(result['ending_probes'][0]['card_field_precedence_verified'])
        self.assertIsNone(result['route_attempt']['successful_route'])
        self.assertEqual(result['buff_effects_resolved'], 0)

    @unittest.skipUnless((DATABASE_DIR / 'db_Reigns.db').exists(), 'Local ConfigDB required')
    def test_direct_cards_localized_text_and_audit(self):
        from wuwa_story.reigns import inspect_reigns
        from wuwa_story.database import rows
        g = inspect_reigns({'Type': 'Reigns', 'ReignsId': 700001}, rows)
        self.assertIn(700042, [c['card_id'] for c in g['cards']])
        title = next(t for t in g['texts'] if t.get('text_id') == 'ReignsCard_700009_CardTitle')
        self.assertIn('test/', title['legacy_inline_text'])
        self.assertNotIn('test/', title['raw_text'])
        self.assertEqual(g['property_names']['3'], '意志')
        self.assertEqual(g['mechanics_audit']['route_attempt']['status'], 'blocked_missing_semantics')
        self.assertFalse(g['route_simulated'])
