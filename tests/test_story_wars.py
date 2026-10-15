"""Actual-script checks for the mandatory AI Gaul route; not engine timing tests."""
import unittest

from tools.validate_diplomacy import EventDelivery, MOD, Runtime, read


class GaulStoryWarTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.runtime.date = "1029.1.1"
        self.scope = self.runtime.scope('LGL')
        self.actor = self.runtime.country('LGL')
        self.runtime.scope('LTH')
        self.target = self.runtime.country('LTH')
        self.actor.completed_focuses.add('LGL_wo4e_start')
        tree = read(MOD / 'common/national_focus/LGL_national_focus.txt')[0]
        self.focuses = {n.scalar('id'): n for n in tree.fields('focus')}
        self.focus = self.focuses['LGL_wo4e_start']

    def start(self):
        self.runtime.call('terra_story_gaul_start_war_effect', self.scope)

    def declarations(self):
        return [n for key, n in self.actor.effects if key == 'declare_war_on']

    def weekly(self):
        hook = read(MOD / 'common/on_actions/terra_diplomacy.txt')[0].one('on_weekly').one('effect')
        self.runtime.execute(hook.children, self.scope)

    def test_focus_retains_player_wargoal_and_schedules_ai_only(self):
        reward = self.focus.one('completion_reward')
        self.assertEqual('LTH', reward.one('create_wargoal').scalar('target'))
        self.runtime.execute(reward.children, self.scope)
        self.assertEqual([EventDelivery('LGL', 'LGL', 'terra_story_wars.1', '1')], self.runtime.deliveries)
        self.actor.attrs['is_ai'] = False
        self.runtime.deliveries.clear()
        self.runtime.execute(reward.children, self.scope)
        self.assertFalse(self.runtime.deliveries)
        self.start()
        self.assertFalse(self.declarations())

    def test_hidden_event_starts_story_war_once_and_never_replays_after_peace(self):
        event = next(n for n in read(MOD / 'events/terra_story_wars.txt') if n.key == 'country_event')
        self.runtime.execute(event.one('immediate').children, self.scope)
        self.assertEqual('LTH', self.declarations()[0].scalar('target'))
        self.assertIn('LGL', self.target.relations['has_defensive_war_with'])
        self.assertIn('terra_story_gaul_war_started', self.actor.flags)
        self.actor.relation('has_war_with', 'LTH', False)
        self.start()
        self.assertEqual(1, len(self.declarations()))

    def test_actual_weekly_hook_repairs_an_already_completed_focus(self):
        self.weekly()
        self.assertEqual(1, len(self.declarations()))

    def daily(self):
        hook = read(MOD / 'common/on_actions/terra_diplomacy.txt')[0].one('on_daily').one('effect')
        self.runtime.execute(hook.children, self.scope)

    def test_1028_preparation_stops_at_final_focus_even_after_envoy_refusal(self):
        self.runtime.date = '1028.1.1'
        self.actor.completed_focuses.clear()
        self.actor.flags.add('LTH_envoy_refuse')
        for _ in range(20): self.weekly()
        self.assertIn('LGL_wo4e_prelude', self.actor.completed_focuses)
        self.assertNotIn('LGL_wo4e_start', self.actor.completed_focuses)
        self.assertFalse(self.runtime.check(self.focus.one('available').children, self.scope))
        self.assertFalse(self.declarations())

    def test_year_boundary_daily_hook_launches_on_january_first_1029(self):
        self.actor.completed_focuses = {'LGL_wo4e_prelude'}
        self.runtime.date = '1028.12.31.23'
        self.daily()
        self.assertFalse(self.declarations())
        self.runtime.date = '1029.1.1'
        self.daily()
        self.assertIn('LGL_wo4e_start', self.actor.completed_focuses)
        self.assertEqual(1, len(self.declarations()))
        self.daily()
        self.assertEqual(1, len(self.declarations()))

    def test_old_completed_wargoal_does_not_trigger_scripted_war_before_1029(self):
        self.runtime.date = '1028.12.31'
        self.start()
        self.assertFalse(self.declarations())
        profile = next(n for n in read(MOD / 'common/ai_strategy/terra_story_wars.txt')
                       if n.key == 'terra_gaul_wait_for_1029')
        self.assertTrue(self.runtime.check(profile.one('enable').children, self.scope))
        self.runtime.date = '1029.1.1'
        self.assertFalse(self.runtime.check(profile.one('enable').children, self.scope))
        self.start()
        self.assertEqual(1, len(self.declarations()))

    def test_existing_war_satisfies_story_and_does_not_restart_after_peace(self):
        self.actor.completed_focuses.clear()
        self.actor.relation('has_war_with', 'LTH')
        self.weekly()
        self.assertIn('terra_story_gaul_war_started', self.actor.flags)
        self.actor.relation('has_war_with', 'LTH', False)
        self.weekly()
        self.assertFalse(self.actor.completed_focuses)
        self.assertFalse(self.declarations())

    def test_sixteen_weekly_pulses_complete_actual_prerequisites_rewards_and_war(self):
        self.actor.completed_focuses.clear()
        plan = read(MOD / 'common/ai_strategy_plans/terra_gaul_four_emperors.txt')[0]
        sequence = [n.key for n in plan.one('ai_national_focuses').children]
        self.assertEqual(16, len(sequence))
        starting_power = self.actor.attrs['political_power']
        for focus in sequence:
            for requirement in self.focuses[focus].fields('prerequisite'):
                self.assertTrue(any(n.value in self.actor.completed_focuses for n in requirement.children), focus)
            before = set(self.actor.completed_focuses)
            self.weekly()
            self.assertEqual({focus}, self.actor.completed_focuses - before)
        self.assertEqual(1, len(self.declarations()))
        self.assertGreater(self.actor.attrs['political_power'], starting_power)
        state = (set(self.actor.completed_focuses), self.actor.attrs['political_power'])
        for _ in range(3): self.weekly()
        self.assertEqual(state, (self.actor.completed_focuses, self.actor.attrs['political_power']))

    def test_existing_friendly_branches_are_not_completed_again_or_turned_aggressive(self):
        self.actor.completed_focuses = {'LGL_start', 'LGL_poli_start', 'LGL_vic_start', 'LGL_vic_1',
            'LGL_vic_2', 'LGL_vic_nonagg_friend', 'LGL_urs_start', 'LGL_urs_1', 'LGL_urs_2',
            'LGL_urs_nonagg_friend'}
        for _ in range(6): self.weekly()
        self.assertEqual(1, len(self.declarations()))
        self.assertNotIn('LGL_vic_nonagg_aggro', self.actor.completed_focuses)
        self.assertNotIn('LGL_urs_nonagg_aggro', self.actor.completed_focuses)

    def test_submission_backdown_missing_goal_and_native_caution_do_not_veto_ai_story(self):
        self.actor.flags.update({'LTH_envoy_submit', 'terra_story_gaul_backed_down', 'terra_state_goal_recovery'})
        self.actor.attrs.update({'has_war': True, 'has_manpower': 5000, 'army_strength': 20})
        self.actor.relation('has_non_aggression_pact_with', 'LTH')
        # No can_declare_war_on or wargoal fixture: this is an explicit scripted war.
        self.start()
        self.assertEqual(1, len(self.declarations()))
        relation = next(n for key, n in self.actor.effects if key == 'diplomatic_relation')
        self.assertEqual(('LTH', 'non_aggression_pact', 'no'),
                         (relation.scalar('country'), relation.scalar('relation'), relation.scalar('active')))
        truce = next(n for key, n in self.actor.effects if key == 'set_truce')
        self.assertEqual('0', truce.scalar('days'))

    def test_shared_faction_is_split_before_declaring_without_removing_other_members(self):
        for leader in ('LGL', 'LTH', 'URS'):
            with self.subTest(leader=leader):
                self.setUp()
                self.runtime.scope('URS')
                ls = self.runtime.scope(leader)
                # Use real faction primitives in the interpreter, not flag-only fixtures.
                from tools.validate_diplomacy import parse
                self.runtime.execute(parse('create_faction = "Fixture"'), ls)
                for member in ('LGL', 'LTH', 'URS'):
                    if member != leader:
                        self.runtime.execute(parse('add_to_faction = ' + member), ls)
                self.start()
                self.assertEqual(1, len(self.declarations()))
                self.assertNotIn('LTH', self.actor.relations.get('is_in_faction_with', set()))
                self.assertEqual(2, len(self.runtime.factions[leader]))

    def test_missing_or_defeated_participants_and_subject_gaul_do_not_start_war(self):
        for participant, attribute in (('LGL', 'exists'), ('LTH', 'exists'),
                                       ('LGL', 'has_capitulated'), ('LTH', 'has_capitulated'),
                                       ('LGL', 'is_subject')):
            with self.subTest(participant=participant, attribute=attribute):
                self.setUp()
                self.runtime.country(participant).attrs[attribute] = attribute != 'exists'
                self.start()
                self.assertFalse(self.declarations())

    def test_human_and_other_countries_do_not_get_forced_focuses_or_wars(self):
        self.actor.attrs['is_ai'] = False
        self.actor.completed_focuses.clear()
        self.weekly()
        self.assertFalse(self.actor.completed_focuses)
        self.assertFalse(self.declarations())
        for tag in self.runtime.countries:
            if tag == 'LGL': continue
            scope = self.runtime.scope(tag)
            country = self.runtime.country(tag)
            self.runtime.call('terra_story_gaul_advance_focus_effect', scope)
            self.assertFalse(country.completed_focuses, tag)
            self.assertFalse(any(k == 'declare_war_on' for k, _ in country.effects), tag)

    def test_wargoal_alone_does_not_authorize_a_story_war_without_the_focus(self):
        self.actor.completed_focuses.clear()
        self.actor.relation('has_wargoal_against', 'LTH')
        self.start()
        self.assertFalse(self.declarations())

    def test_player_backdown_and_submission_still_control_focus_availability(self):
        self.actor.attrs['is_ai'] = False
        self.actor.flags.add('LTH_envoy_refuse')
        self.assertTrue(self.runtime.check(self.focus.one('available').children, self.scope))
        self.actor.flags.add('terra_story_gaul_backed_down')
        self.assertFalse(self.runtime.check(self.focus.one('available').children, self.scope))
        self.actor.flags.add('LTH_envoy_submit')
        skip = self.focuses['LGL_wo4e_skip']
        self.assertTrue(self.runtime.check(skip.one('available').children, self.scope))
        self.actor.attrs['is_ai'] = True
        self.assertTrue(self.runtime.check(self.focus.one('available').children, self.scope))
        self.assertFalse(self.runtime.check(skip.one('available').children, self.scope))


if __name__ == '__main__':
    unittest.main()
