import unittest

from wuwa_story.actor_binding_review import unbound_change_readable, unbound_change_evidence
from wuwa_story.speakers import SpeakerResolver


class ActorBindingReviewTests(unittest.TestCase):
    def setUp(self):
        self.action = {'Name': 'ChangeActorTalker',
                       'Params': {'ActorIndex': 1, 'Talker': 50061}}
        self.items = [{'Type': 'Talk', 'WhoId': 50061, 'TidTalk': 'next'}]

    def test_explicit_speakers_without_actor_table(self):
        self.assertTrue(unbound_change_readable(self.action, [], self.items))
        evidence = unbound_change_evidence(self.action)
        self.assertFalse(evidence['binding_resolved'])
        self.assertFalse(evidence['identity_inferred'])

    def test_no_implicit_speaker_or_unavailable_context(self):
        for items in (None, [], [{'Type': 'Talk'}], [{'Type': 'QTE', 'WhoId': 50061}],
                      [{'Type': 'Talk', 'WhoId': True}], [{'Type': 'Talk', 'WhoId': -1}]):
            self.assertFalse(unbound_change_readable(self.action, [], items))

    def test_existing_or_invalid_actor_table_is_not_overridden(self):
        self.assertFalse(unbound_change_readable(self.action, [{}], self.items))
        self.assertFalse(unbound_change_readable(self.action, None, self.items))

    def test_async_callbacks_and_unknown_fields_rejected(self):
        for action in (dict(self.action, Async=True), dict(self.action, Callbacks=[]),
                       {**self.action, 'Params': {'ActorIndex': -1, 'Talker': 50061}},
                       {**self.action, 'Params': {'ActorIndex': 1, 'Talker': True}},
                       {**self.action, 'Params': {**self.action['Params'], 'Actions': []}}):
            self.assertFalse(unbound_change_readable(action, [], self.items))

    def test_anonymous_identity_is_not_created(self):
        resolver = SpeakerResolver({178: {'name': '？？？', 'source': 'test'},
                                    50061: {'name': 'Known', 'source': 'test'}})
        before = resolver.identify(178)
        self.assertTrue(unbound_change_readable(self.action, resolver.actors, self.items))
        unbound_change_evidence(self.action)
        self.assertEqual(resolver.identify(178), before)
        self.assertEqual(resolver.actors, [])


if __name__ == '__main__':
    unittest.main()
