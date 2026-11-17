import copy
import unittest
from unittest.mock import patch
from wuwa_story.database import rows
from wuwa_story.transition_panels import inspect_transition


def call(board_id=5):
    return {'Name': 'OpenSystemBoard', 'Async': True, 'ActionId': 5000331,
            'Params': {'SystemType': 'TransitionPopup', 'BoardId': board_id}}


class TransitionPanelTests(unittest.TestCase):
    def test_real_source_is_async_attachment(self):
        a = call(); d = inspect_transition(a, rows)
        self.assertEqual([v['text_id'] for v in d['texts']],
                         ['PlotTransitionPopup_5_Title', 'PlotTransitionPopup_5_Text'])
        self.assertEqual([v['raw_text'] for v in d['texts']], ['星炬学院内', '刚刚，通讯的另一边……'])
        self.assertEqual(d['handling'], 'unordered_attachment_at_known_call')
        self.assertFalse(d['display_order_verified'])
        self.assertFalse(d['interleaving_with_dialogue_verified'])
        self.assertEqual(d['call_anchor']['action_id'], 5000331)
        d['source_action']['Params']['BoardId'] = 999
        self.assertEqual(a['Params']['BoardId'], 5)

    def test_execution_and_definition_boundaries(self):
        a = call()
        for extra in [{'Async': False}, {'Async': 1}, {'Timeout': 1}, {'Callback': []}]:
            with self.assertRaises(ValueError): inspect_transition(dict(a, **extra), rows)
        a.pop('Async')
        with self.assertRaises(ValueError): inspect_transition(a, rows)
        for bid in [0, -1, True, '5', 11]:
            with self.assertRaises(ValueError): inspect_transition(call(bid), rows)
        a = call(); a['Params']['Extra'] = True
        with self.assertRaises(ValueError): inspect_transition(a, rows)
        with self.assertRaises(ValueError): inspect_transition(call(), lambda *_: [])
        r = next(r for r in rows('db_TransitionPopup.db', 'transitionpopup') if r['Id'] == 5)
        with self.assertRaises(ValueError): inspect_transition(call(), lambda *_: [r, r])
        broken = copy.deepcopy(r); broken['BinData'] = b'bad'
        with self.assertRaises(ValueError): inspect_transition(call(), lambda *_: [broken])

    def test_missing_or_dynamic_body_is_not_static(self):
        for body in ['', '{world_state}', '%s']:
            with patch('wuwa_story.transition_panels.texts',
                       {'PlotTransitionPopup_5_Title': '标题', 'PlotTransitionPopup_5_Text': body}):
                with self.assertRaises(ValueError): inspect_transition(call(), rows)
