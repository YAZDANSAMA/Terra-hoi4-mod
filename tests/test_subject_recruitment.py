"""Preserved Ta-Netjer story exception. Refunds still need playtesting."""
import unittest
from tools.validate_diplomacy import MOD, Runtime, read


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
        for tag in self.runtime.countries:
            if tag == 'TNJ':
                continue
            with self.subTest(tag=tag):
                self.scope = self.runtime.scope(tag)
                other = self.runtime.country(tag)
                other.attrs['num_divisions'] = 88
                self.daily()
                self.assertEqual(10, self.actor.attrs['num_divisions'])
                self.assertEqual(88, other.attrs['num_divisions'])
                self.assertFalse(other.effects)


if __name__ == '__main__':
    unittest.main()
