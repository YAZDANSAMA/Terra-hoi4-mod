"""Native script guard tests. Recruitment and disband refunds need playtesting."""
import unittest
from tools.validate_diplomacy import MOD, Runtime, read


class SubjectRecruitmentTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.scope = self.runtime.scope('VVA')
        self.actor = self.runtime.country('VVA')
        self.actor.attrs.update({'is_subject': True, 'num_divisions': 21,
                                 'has_manpower': 30000, 'num_of_military_factories': 2})
        self.actor.technologies.add('infantry_weapons')
        self.actor.stockpiles['infantry_equipment'] = 1000

    def eligible(self):
        return self.runtime.trigger('terra_subject_can_recruit_infantry', self.scope)

    def test_vouivre_and_minos_can_request_new_divisions_after_the_starting_army(self):
        for tag, divisions in (('VVA', 21), ('MSN', 15)):
            with self.subTest(tag=tag):
                country = self.runtime.country(tag)
                self.scope = self.runtime.scope(tag)
                country.attrs.update(self.actor.attrs)
                country.attrs['original_tag'] = tag
                country.attrs['num_divisions'] = divisions
                country.technologies.add('infantry_weapons')
                country.stockpiles['infantry_equipment'] = 1000
                self.assertTrue(self.eligible())
        profile = read(MOD / 'common/ai_strategy/terra_subject_recruitment.txt')[0]
        self.assertEqual('yes', profile.scalar('abort_when_not_enabled'))
        self.assertEqual({'build_army', 'force_build_armies', 'ai_wanted_divisions_factor'},
                         {n.scalar('type') for n in profile.fields('ai_strategy')})

    def test_country_size_goal_refreshes_after_expansion_and_war(self):
        self.actor.owned_state_cores = [set() for _ in range(8)]
        self.runtime.call('terra_ai_refresh_capacity_effect', self.scope)
        self.assertEqual(24, self.actor.variables['terra_ai_training_target'])
        self.actor.attrs['num_divisions'] = 24
        self.assertFalse(self.eligible())
        self.actor.attrs['has_war'] = True
        self.runtime.call('terra_ai_refresh_capacity_effect', self.scope)
        self.assertEqual(36, self.actor.variables['terra_ai_training_target'])
        self.assertTrue(self.eligible())
        self.actor.attrs['num_divisions'] = 36
        self.assertFalse(self.eligible())
        self.actor.owned_state_cores.extend([set() for _ in range(4)])
        self.runtime.call('terra_ai_refresh_capacity_effect', self.scope)
        self.assertTrue(self.eligible())

    def test_aid_funded_army_can_train_without_domestic_military_factory(self):
        self.actor.attrs['num_of_military_factories'] = 0
        self.assertTrue(self.eligible())

    def test_training_still_requires_real_men_weapons_and_infantry_technology(self):
        for cause in ('equipment', 'tech', 'manpower', 'human', 'independent', 'capitulated'):
            with self.subTest(cause=cause):
                self.setUp()
                if cause == 'equipment': self.actor.stockpiles['infantry_equipment'] = 750
                elif cause == 'tech': self.actor.technologies.clear()
                elif cause == 'manpower': self.actor.attrs['has_manpower'] = 7500
                elif cause == 'human': self.actor.attrs['is_ai'] = False
                elif cause == 'independent': self.actor.attrs['is_subject'] = False
                else: self.actor.attrs['has_capitulated'] = True
                self.assertFalse(self.eligible())

    def test_all_other_registered_subjects_can_recruit_and_protected_tags_cannot(self):
        for tag in self.runtime.countries:
            self.scope = self.runtime.scope(tag)
            country = self.runtime.country(tag)
            country.attrs.update({'is_subject': True, 'num_divisions': 5,
                                  'has_manpower': 100000, 'num_of_military_factories': 3})
            country.technologies.add('infantry_weapons')
            self.assertEqual(tag not in {'TNJ', 'SST', 'SEA'}, self.eligible(), tag)


class TaNetjerNoArmyTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.scope = self.runtime.scope('TNJ')
        self.actor = self.runtime.country('TNJ')
        self.actor.attrs['num_divisions'] = 10
        self.runtime.scope('SGN')
        self.other = self.runtime.country('SGN')
        self.other.attrs['num_divisions'] = 88

    def daily(self):
        hook = read(MOD / 'common/on_actions/terra_tnj_no_army.txt')[0].one('on_daily').one('effect')
        self.runtime.execute(hook.children, self.scope)

    def test_new_campaign_has_no_tnj_divisions_or_templates(self):
        oob = read(MOD / 'history/units/TNJ_1028.txt')
        self.assertFalse([n for n in oob if n.key == 'division_template'])
        self.assertFalse(oob[0].children)

    def test_old_save_disbands_only_tnj_and_locks_its_policy_once(self):
        self.daily()
        self.assertEqual(0, self.actor.attrs['num_divisions'])
        self.assertEqual(88, self.other.attrs['num_divisions'])
        self.assertFalse(self.actor.rules['can_be_called_to_war'])
        self.assertTrue(self.actor.rules['can_not_declare_war'])
        deletion = next(n for k, n in self.actor.effects if k == 'delete_unit')
        self.assertEqual('yes', deletion.scalar('disband'))
        self.daily()
        self.assertEqual(1, sum(k == 'country_lock_all_division_template' for k, _ in self.actor.effects))
        self.assertEqual(1, sum(k == 'delete_unit' for k, _ in self.actor.effects))

    def test_late_queued_deployment_is_removed_without_world_or_state_scans(self):
        self.daily()
        self.actor.attrs['num_divisions'] = 1
        self.daily()
        self.assertEqual(0, self.actor.attrs['num_divisions'])
        self.assertEqual(88, self.other.attrs['num_divisions'])

    def test_other_country_cannot_execute_tnj_cleanup(self):
        self.scope = self.runtime.scope('SGN')
        self.daily()
        self.assertEqual(10, self.actor.attrs['num_divisions'])
        self.assertEqual(88, self.other.attrs['num_divisions'])
        self.assertFalse(self.other.effects)


if __name__ == '__main__':
    unittest.main()
