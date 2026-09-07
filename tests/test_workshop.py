"""Story invariants, rendered identity, and persistent consequences, offline."""
import unittest

from programs.workshop import Workshop
from pixoolib.runtime import Event
from pixoolib.workshop.story import Story
from pixoolib.workshop.art import CORAL


def advance(story,seconds,dt=.25):
    for _ in range(round(seconds/dt)):story.update(dt)


class StoryTest(unittest.TestCase):
    def test_first_half_minute_makes_a_seed_and_changes_possessions(self):
        s=Story(seed=7);advance(s,26)
        self.assertTrue(s.gear)
        self.assertEqual(s.inventory,'honey')
        self.assertTrue(s.rooms[0].lantern)
        self.assertEqual(s.hat,'nori')
        self.assertEqual(s.completed,1)

    def test_two_world_delivery_has_one_rendered_courier_and_a_consequence(self):
        p=Workshop(worlds='2',show='delivery');p.setup()
        observed=set()
        for _ in range(38*4):
            s=p.story;observed.add(s.courier_room)
            frames=p.render_worlds()
            # The courier's coral scarf is its unique identifying sprite mark
            # during travel; it must never be visible in both rooms together.
            if s.elapsed<20:
                visible=sum(sum(bytes(f.pixels).count(bytes(CORAL)) for _ in [0])>=3 for f in frames)
                self.assertLessEqual(visible,1)
            p.update(.25,[])
        self.assertEqual(observed,{0,1,None})
        self.assertEqual(p.story.courier_room,0)
        self.assertIsNone(p.story.inventory)
        self.assertEqual(p.story.rooms[1].flowers,['honey'])
        self.assertTrue(p.story.rooms[1].lantern)
        self.assertEqual(p.story.deliveries,1)
        self.assertEqual(p.story.rooms[0].flowers,[])
        milestones=[e[1] for e in p.story.events]
        expected=['courier departed','courier arrived','seed planted','courier heading home','courier returned']
        self.assertEqual([e for e in milestones if e in expected],expected)

    def test_single_world_delivery_is_a_complete_local_story(self):
        s=Story(show='delivery');advance(s,38)
        self.assertEqual(s.rooms[0].flowers,['honey'])
        self.assertEqual(s.courier_room,0)
        self.assertEqual(s.deliveries,1)

    def test_friendship_and_tea_change_the_next_invention(self):
        s=Story(show='biscuit');advance(s,27)
        self.assertTrue(s.friend)
        s.request('tea');advance(s,30)
        self.assertEqual(s.brews,1)
        self.assertEqual(s.rooms[0].cups,1)
        self.assertEqual(s.rooms[0].crumbs,0)
        s.request('build');advance(s,26)
        self.assertTrue(s._gentle)
        self.assertNotIn('hat caught',[e[1] for e in s.events])

    def test_showcase_request_does_not_teleport_a_traveler(self):
        s=Story(2,show='delivery');advance(s,11)
        s.request('tea')
        self.assertEqual(s.courier_room,1)
        self.assertEqual(s.episode,'delivery')
        advance(s,27)
        self.assertEqual(s.courier_room,0)
        self.assertEqual(s.pending,'tea')
        advance(s,15)
        self.assertEqual(s.episode,'tea')

    def test_story_does_not_discard_a_ready_gift_for_a_requested_scene(self):
        s=Story(show='build');advance(s,26)
        s.request('tea')
        self.assertEqual(s.episode,'delivery')
        self.assertEqual(s.pending,'tea')
        self.assertEqual(s.inventory,'honey')

    def test_timing_independent_of_preview_rate(self):
        states=[]
        for dt in (.25,.125,.05,1/30):
            s=Story(2,seed=19,demo=True)
            advance(s,180,dt)
            states.append((list(s.events),s.rooms,s.episode,s.elapsed,s.courier(),s.inventory))
        self.assertTrue(all(state==states[0] for state in states))

    def test_rendering_is_repeatable_and_does_not_advance_story(self):
        p=Workshop(worlds='2');p.setup();p.update(15,[])
        before=(p.story.time,p.story.elapsed,list(p.story.events))
        frames=p.render_worlds()
        self.assertEqual([bytes(f.pixels) for f in frames],[bytes(f.pixels) for f in p.render_worlds()])
        self.assertEqual(before,(p.story.time,p.story.elapsed,list(p.story.events)))
        self.assertTrue(all(len(f.pixels)==12288 for f in frames))
        self.assertNotEqual(frames[0].pixels,frames[1].pixels)

    def test_pause_and_reset_controls(self):
        p=Workshop();p.setup();p.update(5,[])
        p.update(3,[Event('key','p')]);self.assertEqual(p.story.time,5)
        p.update(1,[Event('key','p')]);self.assertEqual(p.story.time,6)
        p.update(0,[Event('key','r')]);self.assertEqual(p.story.time,0)

    def test_long_unattended_state_is_bounded_and_varied(self):
        s=Story(2,seed=19,demo=False)
        advance(s,3600,1)
        self.assertGreater(s.builds,5)
        self.assertGreater(s.deliveries,5)
        self.assertGreater(s.brews,3)
        self.assertGreater(s.biscuits,3)
        self.assertLessEqual(len(s.rooms[1].flowers),3)
        self.assertLessEqual(len(s.events),128)
        self.assertLessEqual(s.rooms[0].cups,3)
        self.assertLessEqual(s.rooms[0].crumbs,3)

    def test_invalid_settings(self):
        for params in ({'worlds':'3'},{'seed':'bad'},{'demo':'yes'},{'show':'bad'},{'unknown':'x'}):
            with self.subTest(params=params),self.assertRaises(ValueError):Workshop(**params).setup()
