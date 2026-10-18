"""Aggregate active native policy inputs, rather than checking guards alone.

These tests do not simulate HOI4's queues or its allocation of manpower/guns.
Zero spare rifles is an explicit test input, not a claim about a user's save.
"""
import unittest

from tools.validate_diplomacy import MOD, Runtime, read


class RecruitmentDemandTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.scope = self.runtime.scope('SGN')
        self.actor = self.runtime.country('SGN')
        self.actor.attrs.update(num_divisions=5, num_of_military_factories=6, has_manpower=10000)
        self.actor.technologies.add('infantry_weapons')
        self.actor.stockpiles['infantry_equipment'] = 0
        self.runtime.call('terra_ai_refresh_capacity_effect', self.scope)
        self.policies = []
        for path in (MOD / 'common/ai_strategy').glob('*.txt'):
            for profile in read(path):
                # Inspect all policies that can influence basic land recruitment.
                relevant = [s for s in profile.fields('ai_strategy')
                            if s.scalar('type') in {'force_build_armies', 'ai_wanted_divisions_factor'}
                            or s.scalar('type') in {'role_ratio', 'build_army'}
                            and s.scalar('id') in {'infantry', 'area_defense'}]
                if relevant:
                    self.policies.append((profile, relevant))

    def demand(self):
        totals = {}
        active = []
        for profile, strategies in self.policies:
            allowed = profile.one('allowed')
            enabled = profile.one('enable')
            if ((allowed is None or self.runtime.check(allowed.children, self.scope))
                    and (enabled is None or self.runtime.check(enabled.children, self.scope))):
                active.append(profile.key)
                for s in strategies:
                    key = s.scalar('type'), s.scalar('id')
                    totals[key] = totals.get(key, 0) + int(s.scalar('value'))
        return totals, active

    def test_empty_and_low_rifle_stock_does_not_cancel_basic_roles_or_make_request_negative(self):
        for subject in (False, True):
            self.actor.attrs['is_subject'] = subject
            for rifles in (0, 1, 50, 500, 750, 751, 1000):
                with self.subTest(subject=subject, rifles=rifles):
                    self.actor.stockpiles['infantry_equipment'] = rifles
                    totals, active = self.demand()
                    self.assertGreater(totals.get(('role_ratio', 'infantry'), 0), 0, active)
                    self.assertGreater(totals.get(('role_ratio', 'area_defense'), 0), 0, active)
                    self.assertGreaterEqual(totals.get(('build_army', 'infantry'), 0), 0, active)

    def test_domestic_rifle_industry_can_request_training_before_accumulating_spare_guns(self):
        for subject in (False, True):
            with self.subTest(subject=subject):
                self.actor.attrs['is_subject'] = subject
                totals, active = self.demand()
                self.assertGreater(totals.get(('build_army', 'infantry'), 0), 0, active)
                self.assertGreater(totals.get(('force_build_armies', None), 0), 0, active)
                self.assertFalse(self.runtime.trigger('terra_ai_growth_reserves_ready', self.scope))

    def test_a_country_without_rifle_industry_still_needs_received_equipment_for_extra_request(self):
        self.actor.attrs['num_of_military_factories'] = 0
        self.assertFalse(self.runtime.trigger('terra_ai_can_train_infantry', self.scope))
        self.actor.stockpiles['infantry_equipment'] = 1000
        self.assertTrue(self.runtime.trigger('terra_ai_can_train_infantry', self.scope))
        self.actor.technologies.clear()
        self.assertFalse(self.runtime.trigger('terra_ai_can_train_infantry', self.scope))

    def test_low_manpower_removes_extra_request_without_zeroing_native_infantry_role(self):
        for manpower in (0, 1000, 7500):
            with self.subTest(manpower=manpower):
                self.actor.attrs['has_manpower'] = manpower
                totals, active = self.demand()
                self.assertEqual(0, totals.get(('force_build_armies', None), 0), active)
                self.assertGreater(totals.get(('role_ratio', 'infantry'), 0), 0, active)
                self.assertGreaterEqual(totals.get(('build_army', 'infantry'), 0), 0, active)

    def test_basic_roles_survive_rifle_shortage_for_every_registered_country_and_subject(self):
        for tag in list(self.runtime.countries):
            self.scope = self.runtime.scope(tag)
            self.actor = self.runtime.country(tag)
            self.actor.attrs.update(num_divisions=5, num_of_military_factories=3, has_manpower=10000)
            self.actor.technologies.add('infantry_weapons')
            self.actor.stockpiles['infantry_equipment'] = 0
            self.runtime.call('terra_ai_refresh_capacity_effect', self.scope)
            for subject in (False, True):
                with self.subTest(tag=tag, subject=subject):
                    self.actor.attrs['is_subject'] = subject
                    totals, active = self.demand()
                    if tag in {'TNJ', 'SST', 'SEA'}:
                        self.assertLessEqual(totals.get(('force_build_armies', None), 0), 0, active)
                    else:
                        self.assertGreater(totals.get(('role_ratio', 'infantry'), 0), 0, active)
                        self.assertGreaterEqual(totals.get(('build_army', 'infantry'), 0), 0, active)

    def test_real_starting_armies_keep_basic_roles_when_spare_rifles_are_empty(self):
        # Reuse the real state/OOB/law fixture, including transferred western
        # garrisons, without replacing their actual factory counts.
        from tests.test_global_ai_repair import GlobalAIRepairTests
        fixture = GlobalAIRepairTests()
        fixture.setUp()
        for tag in ('SGN', 'MSN', 'PSE', 'VVA', 'GRM', 'HTR', 'PLM'):
            with self.subTest(tag=tag):
                fixture.load_history(tag)
                self.runtime, self.scope, self.actor = fixture.runtime, fixture.scope, fixture.actor
                self.actor.stockpiles['infantry_equipment'] = 0
                totals, active = self.demand()
                self.assertGreater(totals.get(('role_ratio', 'infantry'), 0), 0, active)
                self.assertGreaterEqual(totals.get(('build_army', 'infantry'), 0), 0, active)
                if tag in {'SGN', 'MSN'}:
                    self.assertGreater(totals.get(('force_build_armies', None), 0), 0, active)
                if self.actor.attrs['num_of_military_factories'] == 0:
                    self.assertEqual(0, totals.get(('force_build_armies', None), 0), active)

    def test_bootstrap_requests_do_not_apply_to_player_capitulated_or_landless_country(self):
        for cause in ('player', 'capitulated', 'landless'):
            with self.subTest(cause=cause):
                self.setUp()
                if cause == 'player': self.actor.attrs['is_ai'] = False
                elif cause == 'capitulated': self.actor.attrs['has_capitulated'] = True
                else: self.actor.owned_state_cores = []
                totals, active = self.demand()
                self.assertEqual(0, totals.get(('force_build_armies', None), 0), active)

    def test_legacy_recruitment_lock_is_disabled_and_can_abort_in_existing_saves(self):
        old = next(p for p, _ in self.policies if p.key == 'terra_ai_refill_before_recruiting')
        self.assertEqual('yes', old.scalar('abort_when_not_enabled'))
        for manpower, rifles in ((0, 0), (10000, 0), (100000, 10000)):
            self.actor.attrs['has_manpower'] = manpower
            self.actor.stockpiles['infantry_equipment'] = rifles
            self.assertFalse(self.runtime.check(old.one('enable').children, self.scope))
            self.assertNotIn(old.key, self.demand()[1])


if __name__ == '__main__':
    unittest.main()
