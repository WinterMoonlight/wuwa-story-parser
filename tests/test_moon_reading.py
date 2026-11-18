import unittest

from wuwa_story.mainline_reading import build_mainline_reading, mainline_reading_text
from wuwa_story.reading_cases.moon import DARK, FIRST, FOLLOWUP_INVITATION, INVITATION, SECOND
from wuwa_story.recap_backbone import export_task_backbone


class MoonReadingTests(unittest.TestCase):
    def test_four_database_drafts_have_expected_text_and_stay_unverified_at_runtime(self):
        for quest_id, count in ((880000017, 235), (880000021, 108),
                                (880000025, 118), (880000032, 402)):
            with self.subTest(quest_id=quest_id):
                result = export_task_backbone(quest_id)
                view = build_mainline_reading(result)
                self.assertEqual(view['ordering_basis'], 'database_dialogue_continuity')
                self.assertEqual(view['status'], 'ordered_draft_with_gaps')
                self.assertEqual(view['retained_text_events'], count)
                self.assertFalse(view['runtime_verified'])
                self.assertFalse(result['batch_coverage']['order']['selected_route_verified'])
                self.assertEqual(result['events'], [])
                if quest_id == 880000032:
                    draft = result['moon_reading_draft']
                    self.assertEqual(draft['dungeon']['levelplay_id'], 139000001)
                    order = [e.get('flow') for e in draft['entries']]
                    self.assertLess(order.index(DARK + '1_35'), order.index(DARK + '1_50'))
                    self.assertLess(order.index(DARK + '3_1'), order.index(SECOND + '4_5'))
                    self.assertIn(SECOND + '4_7', draft['other_task_references'])
                    self.assertNotIn(SECOND + '4_7', order)
                    entries = {e.get('flow'): e for e in draft['entries']}
                    self.assertEqual(order[order.index(DARK + '1_38') + 1:order.index(DARK + '1_9')],
                                     [DARK + suffix for suffix in ('1_51', '1_47', '1_48')])
                    papers = [event['information_board']['board_id']
                              for suffix in ('1_51', '1_47')
                              for event in entries[DARK + suffix]['segment']['events']
                              if event['kind'] == 'information_board']
                    self.assertEqual(papers, list(range(120101015, 120101020)))
                    self.assertEqual(order[order.index(DARK + '1_45') + 1:order.index(DARK + '1_28')],
                                     [DARK + suffix for suffix in ('1_23', '1_22', '1_24', '1_25', '1_26')])
                    self.assertEqual(order[order.index(DARK + '1_29') + 1:order.index(DARK + '1_35')],
                                     [DARK + suffix for suffix in ('1_30', '2_1', '1_32', '1_31', '2_2')])
                    self.assertEqual(entries[DARK + '1_32']['call_site']['path'][1], 128)
                    self.assertEqual(entries[DARK + '1_32']['equivalent_call_sites'][0]['path'][1], 130)
                    self.assertEqual(view['omission_markers'], 2)
                    for suffix, asset in (('2_1', 'DA_R0012'), ('2_2', 'DA_R0014')):
                        event, = entries[DARK + suffix]['segment']['events']
                        self.assertEqual(event['kind'], 'media_reference')
                        self.assertTrue(event['source_resolution']['asset_path'].endswith(f'/{asset}.{asset}'))
                        self.assertFalse(event['source_resolution']['asset_content_decoded'])

    def test_declining_does_not_skip_straight_to_meeting_the_grandmother(self):
        choices = {INVITATION + ':19': 1, FOLLOWUP_INVITATION + ':1': 1}
        result = export_task_backbone(880000021, choices)
        steps = result['moon_reading_draft']['entries']
        self.assertIn(FOLLOWUP_INVITATION, [entry.get('flow') for entry in steps])
        self.assertIn(FIRST + '7_4', result['moon_reading_draft']['other_task_references'])
        self.assertIn('尚未答应出发', mainline_reading_text(result))
