from copy import deepcopy
import unittest
from unittest.mock import Mock

from wuwa_story.reading_cases.jinzhou import STORYTELLER, YUEHUI, build_jinzhou_draft
from wuwa_story.mainline_reading import build_mainline_reading, mainline_reading_text
from wuwa_story.recap_backbone import export_task_backbone


class JinzhouReadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = export_task_backbone(140800000)

    def test_real_scene_places_narration_and_optional_dialogue_between_scene_boundaries(self):
        draft = self.result['jinzhou_reading_draft']
        view = build_mainline_reading(self.result)
        self.assertEqual(view['status'], 'ordered_draft_with_gaps')
        self.assertEqual(view['retained_text_events'], 27)
        self.assertEqual([entry['segment']['state_key'] for entry in draft['entries'] if 'segment' in entry],
                         [STORYTELLER, YUEHUI])
        self.assertFalse(draft['runtime_order_verified'])
        self.assertFalse(draft['scene_evidence']['narration_direct_trigger_found'])
        self.assertFalse(draft['scene_evidence']['yuehui_interaction_mandatory_verified'])
        self.assertEqual(self.result['events'], [])
        self.assertIn('可选交谈 · 岳辉', mainline_reading_text(self.result))

    def test_no_draft_when_chapter_exit_prerequisite_changes(self):
        quest = self.result['source']['quest_definition']
        nodes = deepcopy(self.result['source']['task_nodes'])
        finish = next(n for n in nodes if n['Id'] == 330)
        finish['Condition']['Conditions'][0]['EntityId'] = 140800592
        source = Mock()
        self.assertIsNone(build_jinzhou_draft(self.result, quest, nodes, {}, source, None))
        source.rows.assert_not_called()
