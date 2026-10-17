"""Policy regressions using current map, OOB and technology data.

History manpower estimates assume the native base conscription fractions and
1,000 men per infantry battalion. These explicit assumptions are not a simulation
of mobilization, queues, equipment delivery, field supply or native AI scheduling.
"""
from functools import lru_cache
import itertools
import unittest

from tools.validate_diplomacy import MOD, Runtime, read, walk


@lru_cache(None)
def history_inputs(tag):
    history = read(next((MOD / 'history/countries').glob(f'{tag} - *.txt')))
    states = []
    for path in (MOD / 'history/states').glob('*.txt'):
        state = read(path)[0]
        if state.one('history').scalar('owner') == tag:
            states.append(state)
    oob = read(MOD / f'history/units/{next(n.value for n in history if n.key == "oob")}.txt')
    templates = {n.scalar('name'): n for n in oob if n.key == 'division_template'}
    divisions = next(n for n in oob if n.key == 'units').fields('division')
    army_men = 0
    for division in divisions:
        regiments = templates[division.scalar('division_template')].one('regiments').children
        if any(n.key != 'infantry' for n in regiments):
            raise AssertionError('History manpower fixture needs an explicit unit-cost assumption')
        army_men += len(regiments) * 1000 * float(division.scalar('start_manpower_factor', '1'))
    population = sum(int(s.scalar('manpower')) for s in states
                     if any(n.value == tag for n in s.one('history').fields('add_core_of')))
    ideas = {n.value for n in history if n.key == 'add_ideas' and isinstance(n.value, str)}
    ideas.update(c.key for n in history if n.key == 'add_ideas' and not isinstance(n.value, str) for c in n.children)
    rate = 0.025 if 'limited_conscription' in ideas else 0.015 if 'volunteer_only' in ideas else None
    if rate is None:
        raise AssertionError('History fixture needs explicit conscription-law input')
    buildings = {}
    for state in states:
        block = state.one('history').one('buildings')
        if block is not None:
            for n in block.children:
                if isinstance(n.value, str): buildings[n.key] = buildings.get(n.key, 0) + int(n.value)
    return history, states, len(divisions), population * rate - army_men, buildings


class GlobalAIRepairTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.scope = self.runtime.scope('SGN')
        self.actor = self.runtime.country('SGN')

    def profile(self, name, filename):
        node = next(n for n in read(MOD / 'common/ai_strategy' / filename) if n.key == name)
        return (self.runtime.check(node.one('allowed').children, self.scope)
                and self.runtime.check(node.one('enable').children, self.scope))

    def load_history(self, tag):
        self.scope = self.runtime.scope(tag)
        self.actor = self.runtime.country(tag)
        history, states, divisions, manpower, buildings = history_inputs(tag)
        self.actor.owned_state_cores = [{n.value for n in s.one('history').fields('add_core_of')} for s in states]
        self.actor.attrs.update(num_divisions=divisions, has_manpower=manpower,
                                num_of_military_factories=buildings.get('arms_factory', 0),
                                num_of_civilian_factories=buildings.get('industrial_complex', 0),
                                is_subject=any(not isinstance(n.value, str) and
                                               any(c.key == 'puppet' and c.value == tag for c in n.children)
                                               for n in history))
        self.actor.technologies = {n.key for block in history if block.key == 'set_technology' for n in block.children if n.value == '1'}
        # Test aid stocks are explicit, never inferred from the full equipment
        # factors of already deployed starting divisions.
        self.actor.stockpiles = {'infantry_equipment': 1000}
        for n in history:
            if n.key.endswith(('_initialize_reserves_effect', '_initialize_transferred_army_effect')):
                self.runtime.call(n.key, self.scope)
        self.runtime.call('terra_ai_refresh_capacity_effect', self.scope)

    def test_real_vouivre_zero_factory_start_can_use_donated_rifles(self):
        self.load_history('VVA')
        self.assertEqual(0, self.actor.attrs['num_of_military_factories'])
        self.assertEqual(3, self.actor.attrs['num_of_civilian_factories'])
        self.assertEqual(21, self.actor.attrs['num_divisions'])
        self.assertGreater(self.actor.attrs['has_manpower'], 370000)
        self.assertTrue(self.runtime.trigger('terra_subject_can_recruit_infantry', self.scope))
        self.assertTrue(self.profile('terra_ai_first_military_factory', 'terra_ai_strategy.txt'))
        self.assertFalse(self.profile('terra_ai_civilian_foundation', 'terra_ai_strategy.txt'))
        self.actor.stockpiles['infantry_equipment'] = 0
        self.assertFalse(self.runtime.trigger('terra_subject_can_recruit_infantry', self.scope))

    def test_real_minos_ten_thousand_free_men_no_longer_hit_fifteen_thousand_gate(self):
        self.load_history('MSN')
        self.assertEqual(15, self.actor.attrs['num_divisions'])
        self.assertEqual(10000, self.actor.attrs['has_manpower'])
        self.assertTrue(self.runtime.trigger('terra_subject_can_recruit_infantry', self.scope))
        self.assertFalse(self.profile('terra_ai_refill_before_recruiting', 'terra_ai_strategy.txt'))
        # Spending the baseline six-battalion manpower cost leaves too little
        # for another request. The evaluator does not simulate actual training.
        self.actor.attrs['has_manpower'] -= 6000
        self.assertFalse(self.runtime.trigger('terra_subject_can_recruit_infantry', self.scope))
        self.assertTrue(self.profile('terra_ai_refill_before_recruiting', 'terra_ai_strategy.txt'))

    def test_real_athura_three_factory_start_can_replace_trains_without_freezing_front(self):
        self.load_history('PSE')
        self.runtime.call('terra_dip_initialize_effect', self.scope)
        self.actor.attrs['has_war'] = True
        self.actor.stockpiles.update(infantry_equipment=2000, train_equipment=0)
        self.assertEqual(3, self.actor.attrs['num_of_military_factories'])
        self.assertEqual(22, self.actor.attrs['num_divisions'])
        self.assertTrue(self.profile('terra_ai_trains_line', 'terra_ai_production.txt'))
        self.assertTrue(self.profile('terra_ai_rifle_floor_small', 'terra_ai_production.txt'))
        self.assertFalse(self.runtime.trigger('terra_war_recovery_required', self.scope))
        self.assertTrue(self.profile('terra_war_prepared_front', 'terra_war_director.txt'))

    def test_sargon_current_start_reserves_and_tnj_sanctuary_are_preserved(self):
        self.load_history('SGN')
        self.assertEqual(27, self.actor.attrs['num_divisions'])
        # The latest scenario transfers the western garrisons to three new
        # owners; the original combined force must not be lost or duplicated.
        self.assertEqual(66, self.actor.attrs['num_divisions'] +
                         sum(history_inputs(tag)[2] for tag in ('GRM', 'HTR', 'PLM')))
        self.assertAlmostEqual(2000000, self.actor.attrs['has_manpower'], delta=1)
        self.load_history('TNJ')
        self.assertEqual(0, self.actor.attrs['num_divisions'])
        self.assertFalse(self.runtime.trigger('terra_ai_can_train_infantry', self.scope))
        self.assertNotIn('terra_ai_training_target', self.actor.variables)

    def test_western_satrapies_use_transferred_reserves_and_can_train_with_aid_at_war(self):
        for tag, divisions in (('GRM', 15), ('HTR', 13), ('PLM', 11)):
            with self.subTest(tag=tag):
                self.load_history(tag)
                self.assertTrue(self.actor.attrs['is_subject'])
                self.assertEqual(divisions, self.actor.attrs['num_divisions'])
                self.assertEqual(0, self.actor.attrs['num_of_military_factories'])
                self.assertGreater(self.actor.attrs['has_manpower'], 7500)
                before = self.actor.attrs['has_manpower']
                history = history_inputs(tag)[0]
                for node in history:
                    if node.key.endswith('_initialize_transferred_army_effect'):
                        self.runtime.call(node.key, self.scope)
                self.assertEqual(before, self.actor.attrs['has_manpower'])
                self.actor.attrs['has_war'] = True
                self.runtime.call('terra_ai_refresh_capacity_effect', self.scope)
                self.assertTrue(self.runtime.trigger('terra_subject_can_recruit_infantry', self.scope))
                self.actor.stockpiles['infantry_equipment'] = 0
                self.assertFalse(self.runtime.trigger('terra_subject_can_recruit_infantry', self.scope))

    def test_all_registered_military_countries_keep_template_and_designer_coverage(self):
        expected = set(self.runtime.countries) - {'SST', 'SEA', 'TNJ'}
        for directory in ('ai_templates', 'ai_equipment'):
            for path in (MOD / 'common' / directory).glob('terra_*.txt'):
                for profile in read(path):
                    countries = profile.one('available_for')
                    if countries is not None:
                        self.assertLessEqual(expected, {n.key for n in countries.children},
                                             f'{path.name}: {profile.key}')

    def test_ordinary_countries_receive_paid_growth_without_stacking_subject_request(self):
        self.actor.technologies.add('infantry_weapons')
        self.actor.attrs['num_divisions'] = 5
        self.runtime.call('terra_ai_refresh_capacity_effect', self.scope)
        self.assertTrue(self.profile('terra_ai_recruit_infantry', 'terra_ai_strategy.txt'))
        self.assertFalse(self.profile('terra_subject_recruit_infantry', 'terra_subject_recruitment.txt'))
        self.actor.attrs['is_subject'] = True
        self.assertFalse(self.profile('terra_ai_recruit_infantry', 'terra_ai_strategy.txt'))
        self.assertTrue(self.profile('terra_subject_recruit_infantry', 'terra_subject_recruitment.txt'))
        self.actor.attrs['num_divisions'] = 0
        self.assertFalse(self.profile('terra_ai_recruit_first_division', 'terra_ai_strategy.txt'))
        self.assertTrue(self.profile('terra_subject_recruit_infantry', 'terra_subject_recruitment.txt'))
        self.actor.attrs['is_subject'] = False
        self.assertTrue(self.profile('terra_ai_recruit_first_division', 'terra_ai_strategy.txt'))

    def test_capacity_is_bounded_and_does_not_grant_units_men_or_guns(self):
        before = (dict(self.actor.attrs), dict(self.actor.stockpiles))
        self.actor.owned_state_cores = [set() for _ in range(200)]
        self.runtime.call('terra_ai_refresh_capacity_effect', self.scope)
        self.assertEqual(96, self.actor.variables['terra_ai_training_target'])
        self.assertEqual(before, (dict(self.actor.attrs), dict(self.actor.stockpiles)))
        self.actor.attrs['has_war'] = True
        self.runtime.call('terra_ai_refresh_capacity_effect', self.scope)
        self.assertEqual(144, self.actor.variables['terra_ai_training_target'])
        self.actor.owned_state_cores = []
        self.actor.variables.clear()
        self.runtime.call('terra_ai_refresh_capacity_effect', self.scope)
        self.assertFalse(self.actor.variables)

    def test_large_army_does_not_use_small_country_reserve_threshold(self):
        self.actor.attrs.update(num_divisions=100, has_manpower=10000)
        self.actor.technologies.add('infantry_weapons')
        self.runtime.call('terra_ai_refresh_capacity_effect', self.scope)
        self.assertEqual(25000, self.actor.variables['terra_ai_manpower_reserve'])
        self.assertEqual(1500, self.actor.variables['terra_ai_rifle_reserve'])
        self.assertFalse(self.runtime.trigger('terra_ai_can_train_infantry', self.scope))
        self.assertTrue(self.profile('terra_ai_refill_before_recruiting', 'terra_ai_strategy.txt'))
        self.actor.attrs['has_manpower'] = 25001
        self.actor.stockpiles['infantry_equipment'] = 1500
        self.assertFalse(self.runtime.trigger('terra_ai_can_train_infantry', self.scope))
        self.actor.stockpiles['infantry_equipment'] = 1501
        self.assertTrue(self.runtime.trigger('terra_ai_can_train_infantry', self.scope))
        self.assertFalse(self.profile('terra_ai_refill_before_recruiting', 'terra_ai_strategy.txt'))

    def test_one_factory_country_alternates_rifle_and_train_floor_with_real_reserve(self):
        self.actor.attrs.update(num_of_military_factories=1, num_divisions=8)
        self.actor.technologies.update({'basic_train', 'infantry_weapons'})
        for rifles, trains, expected in ((0, 0, (True, False)), (1500, 0, (True, False)),
                                          (1501, 0, (False, True)), (1501, 5, (True, False))):
            with self.subTest(rifles=rifles, trains=trains):
                self.actor.stockpiles.update(infantry_equipment=rifles, train_equipment=trains)
                self.assertEqual(expected, (
                    self.profile('terra_ai_rifle_floor_small', 'terra_ai_production.txt'),
                    self.profile('terra_ai_trains_line', 'terra_ai_production.txt')))

    def test_military_factory_floors_fit_tiny_and_large_industry_with_and_without_designers(self):
        files = ['terra_ai_strategy.txt', 'terra_ai_production.txt']
        policies = [n for f in files for n in read(MOD / 'common/ai_strategy' / f)
                    if any(s.scalar('type') == 'equipment_production_min_factories_archetype' for s in n.fields('ai_strategy'))]
        techs = {n.value for p in policies for n in walk((p,)) if n.key == 'has_tech'}
        self.actor.technologies.update(techs)
        self.actor.attrs.update(air_base=1, fuel_ratio=1)
        for factories, rifles, designers in itertools.product((1, 2, 3, 4, 6, 8, 12, 20, 40), (0, 1000, 2000), (False, True)):
            with self.subTest(factories=factories, rifles=rifles, designers=designers):
                self.runtime.dlcs = {'No Step Back', 'By Blood Alone'} if designers else set()
                self.actor.attrs['num_of_military_factories'] = factories
                self.actor.stockpiles['infantry_equipment'] = rifles
                floors = sum(int(s.scalar('value')) for p in policies
                             if self.runtime.check(p.one('enable').children, self.scope)
                             for s in p.fields('ai_strategy') if s.scalar('type') == 'equipment_production_min_factories_archetype')
                self.assertLessEqual(floors, factories)

    def test_exhausted_subject_keeps_call_duty_but_stops_forced_foreign_front_allocation(self):
        self.runtime.call('terra_dip_initialize_effect', self.scope)
        self.runtime.call('terra_state_initialize_effect', self.scope)
        self.runtime.scope('URS')
        self.actor.attrs.update(is_subject=True, has_war=True)
        self.actor.relation('is_subject_of', 'URS')
        self.actor.relation('has_war_together_with', 'URS')
        self.assertTrue(self.profile('terra_state_subject_front_support_URS', 'terra_strategic_state.txt'))
        self.actor.variables['terra_state_fatigue'] = 90
        self.assertFalse(self.profile('terra_state_subject_front_support_URS', 'terra_strategic_state.txt'))
        self.actor.relation('has_war_together_with', 'URS', False)
        self.runtime.country('URS').attrs['has_war'] = True
        self.assertTrue(self.profile('terra_state_subject_loyalty_URS', 'terra_strategic_state.txt'))

    def test_air_readiness_accepts_gifted_aircraft_country_but_requires_base_and_fuel(self):
        self.actor.attrs.update(has_war=True, num_of_military_factories=0, air_base=1, fuel_ratio=0.5)
        self.assertTrue(self.runtime.trigger('terra_ai_air_ready', self.scope))
        for field, value in (('air_base', 0), ('fuel_ratio', 0.1), ('is_ai', False), ('has_war', False)):
            before = self.actor.attrs[field]
            self.actor.attrs[field] = value
            self.assertFalse(self.runtime.trigger('terra_ai_air_ready', self.scope), field)
            self.actor.attrs[field] = before

    def test_every_land_air_region_has_home_defense_and_front_priority(self):
        land_provinces = {n.key for p in (MOD / 'history/states').glob('*.txt')
                          for n in read(p)[0].one('provinces').children}
        land = {read(p)[0].scalar('id') for p in (MOD / 'map/strategicregions').glob('*.txt')
                if land_provinces & {n.key for n in read(p)[0].one('provinces').children}}
        profiles = read(MOD / 'common/ai_strategy/terra_ai_air_operations.txt')
        fronts = {n.key.removeprefix('terra_ai_air_front_'): n for n in profiles if n.key.startswith('terra_ai_air_front_')}
        homes = {n.key.removeprefix('terra_ai_air_home_'): n for n in profiles if n.key.startswith('terra_ai_air_home_')}
        self.assertEqual(land, set(fronts))
        self.assertEqual(land, set(homes))
        for region in land:
            self.assertGreater(int(homes[region].one('ai_strategy').scalar('value')), int(fronts[region].one('ai_strategy').scalar('value')))

    def test_capital_ship_requests_require_industry_fuel_hulls_and_surplus(self):
        name = 'terra_ai_carrier_fleet_budget'
        file = 'terra_ai_navy.txt'
        self.actor.attrs.update(num_of_naval_factories=25, num_of_military_factories=30, naval_base=1, fuel_ratio=0.5)
        self.actor.technologies.add('basic_ship_hull_carrier')
        self.assertTrue(self.profile(name, file))
        for field, value in (('num_of_naval_factories', 24), ('num_of_military_factories', 29), ('fuel_ratio', 0.25)):
            before = self.actor.attrs[field]
            self.actor.attrs[field] = value
            self.assertFalse(self.profile(name, file), field)
            self.actor.attrs[field] = before
        self.actor.stockpiles['infantry_equipment'] = 100
        self.assertFalse(self.profile(name, file))

    def test_convoy_replacement_releases_its_dockyard_when_buffer_recovers(self):
        self.actor.attrs.update(num_of_naval_factories=1, naval_base=1)
        self.actor.equipment['convoy'] = 0
        self.assertTrue(self.profile('terra_ai_convoy_emergency', 'terra_ai_navy.txt'))
        self.actor.equipment['convoy'] = 0.5
        self.assertFalse(self.profile('terra_ai_convoy_emergency', 'terra_ai_navy.txt'))

    def test_every_subject_front_profile_obeys_home_defense_without_restricting_call_loyalty(self):
        policies = read(MOD / 'common/ai_strategy/terra_strategic_state.txt')
        fronts = [n for n in policies if n.key.startswith('terra_state_subject_front_support_')]
        partners = set(self.runtime.countries) - {'SST', 'SEA'}
        self.assertEqual(partners, {n.key.removeprefix('terra_state_subject_front_support_') for n in fronts})
        for node in fronts:
            self.assertIsNotNone(node.one('enable').one('terra_war_can_spare_allied_force'))
        loyalty = [n for n in policies if n.key.startswith('terra_state_subject_loyalty_')]
        self.assertEqual(partners, {n.key.removeprefix('terra_state_subject_loyalty_') for n in loyalty})
        for node in loyalty:
            self.assertIsNone(node.one('enable').one('terra_war_can_spare_allied_force'))

    def test_recovery_front_allows_counterattacks_and_overrides_opportunity_priority(self):
        policies = {n.key: n for n in read(MOD / 'common/ai_strategy/terra_war_director.txt')}
        conserve = policies['terra_war_conserve_front'].one('ai_strategy')
        opportunity = policies['terra_war_opportunity_URS'].one('ai_strategy')
        self.assertEqual('careful', conserve.scalar('execution_type'))
        self.assertEqual('yes', conserve.scalar('manual_attack'))
        self.assertGreater(int(conserve.scalar('priority')), int(opportunity.scalar('priority')))

    def test_designers_keep_dlc_tech_and_budget_requirements(self):
        cases = [('terra_planes_designs.txt', 'terra_design_generic_fighter', 'By Blood Alone', 'basic_small_airframe', 'num_of_military_factories', 5),
                 ('terra_tank_designs.txt', 'terra_design_generic_light_tanks', 'No Step Back', 'basic_light_tank_chassis', 'num_of_military_factories', 6),
                 ('terra_naval_designs.txt', 'terra_design_destroyers', 'Man the Guns', 'basic_ship_hull_light', 'num_of_naval_factories', 1)]
        for file, name, dlc, tech, field, minimum in cases:
            with self.subTest(designer=name):
                node = next(n for n in read(MOD / 'common/ai_equipment' / file) if n.key == name)
                enable = next(n.one('enable') for n in node.children if not isinstance(n.value, str) and n.one('enable') is not None)
                self.runtime.dlcs = {dlc}
                self.actor.technologies = {tech}
                self.actor.attrs.update(num_of_military_factories=20, num_of_naval_factories=20, naval_base=1)
                self.assertTrue(self.runtime.check(enable.children, self.scope))
                self.actor.attrs[field] = minimum - 1
                self.assertFalse(self.runtime.check(enable.children, self.scope))
                self.actor.attrs[field] = minimum
                self.runtime.dlcs.clear()
                self.assertFalse(self.runtime.check(enable.children, self.scope))
                self.runtime.dlcs.add(dlc)
                self.actor.technologies.clear()
                self.assertFalse(self.runtime.check(enable.children, self.scope))

    def test_seaborn_keeps_its_existing_design_policy_outside_generic_budgets(self):
        self.scope = self.runtime.scope('SEA')
        self.actor = self.runtime.country('SEA')
        self.actor.attrs.update(num_of_military_factories=1, num_of_naval_factories=1, naval_base=1)
        self.actor.stockpiles['infantry_equipment'] = 0
        self.runtime.dlcs = {'No Step Back', 'By Blood Alone', 'Man the Guns'}
        for path in (MOD / 'common/ai_equipment').glob('terra_*_designs.txt'):
            for root in read(path):
                for variant in root.children:
                    if isinstance(variant.value, str):
                        continue
                    enable = variant.one('enable')
                    if enable is None:
                        continue
                    with self.subTest(design=root.key):
                        self.actor.technologies = {n.value for n in walk((enable,)) if n.key == 'has_tech'}
                        self.assertTrue(self.runtime.check(enable.children, self.scope))
                        self.runtime.dlcs.clear()
                        self.assertFalse(self.runtime.check(enable.children, self.scope))
                        self.runtime.dlcs = {'No Step Back', 'By Blood Alone', 'Man the Guns'}

    def test_research_works_for_country_with_owned_state_and_releases_when_it_loses_land(self):
        node = next(n for n in read(MOD / 'common/ai_strategy/terra_ai_research.txt') if n.one('enable') is not None)
        # This executes the native trigger block; the former misspelled trigger
        # would fail loudly here rather than being silently assumed true.
        self.assertTrue(self.runtime.check(node.one('enable').children, self.scope))
        self.actor.owned_state_cores = []
        self.assertFalse(self.runtime.check(node.one('enable').children, self.scope))


if __name__ == '__main__':
    unittest.main()
