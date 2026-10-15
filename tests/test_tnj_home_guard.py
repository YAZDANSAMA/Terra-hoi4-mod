"""Geographic script fixtures, not native pathfinding/teleport verification."""
import unittest

from tools.validate_diplomacy import MOD, Runtime, Scope, read


class GuardRuntime(Runtime):
    """Execute the actual AST with explicit state/army fixtures and native scopes."""
    def __init__(self):
        super().__init__()
        # id -> (owner, controller); include an occupied home and foreign land.
        self.states = {170: ('TNJ', 'TNJ'), 172: ('TNJ', 'TNJ'),
                       179: ('TNJ', 'SGN'), 171: ('SGN', 'SGN'), 200: ('CLM', 'CLM')}
        # id -> (army owner, location). Army controller is intentionally not used:
        # teleport_armies.limit is documented to scope the owner of the army.
        self.armies = {'guard_home': ('TNJ', 170), 'guard_abroad': ('TNJ', 171),
                       'guard_enemy': ('TNJ', 200), 'guard_occupied_home': ('TNJ', 179),
                       'royal_army': ('SGN', 171), 'foreign_army': ('CLM', 200)}

    def condition(self, node, scope):
        if scope.current.startswith('fixture_state:'):
            state = int(scope.current.split(':')[1])
            if node.key == 'NOT': return not self.check(node.children, scope)
            if node.key == 'is_owned_by': return self.states[state][0] == node.value
            raise AssertionError('Unsupported fixture state predicate: ' + node.key)
        return super().condition(node, scope)

    def execute(self, nodes, scope):
        for node in nodes:
            if node.key == 'random_owned_controlled_state':
                choices = [state for state, pair in self.states.items() if pair == (scope.current, scope.current)]
                if choices:
                    self.execute(node.children, scope.switch('fixture_state:' + str(choices[0])))
            elif node.key == 'every_state':
                for state in self.states:
                    ss = scope.switch('fixture_state:' + str(state))
                    limit = node.one('limit')
                    if limit is None or self.check(limit.children, ss):
                        self.execute(tuple(n for n in node.children if n.key != 'limit'), ss)
            elif node.key == 'teleport_armies':
                self.assert_state_scope(scope.current)
                source = int(scope.current.split(':')[1])
                destination = self.resolve(node.scalar('to_state'), scope)
                self.assert_state_scope(destination)
                destination = int(destination.split(':')[1])
                for army, (owner, state) in list(self.armies.items()):
                    if state == source and self.check(node.one('limit').children, scope.switch(owner)):
                        self.armies[army] = owner, destination
            elif node.key == 'country_lock_all_division_template':
                self.country(scope.current).effects.append((node.key, node))
            else:
                super().execute((node,), scope)

    @staticmethod
    def assert_state_scope(value):
        if not value.startswith('fixture_state:'):
            raise AssertionError('Expected state scope, received ' + value)


class HomeGuardTests(unittest.TestCase):
    def setUp(self):
        self.runtime = GuardRuntime()
        self.scope = self.runtime.scope('TNJ')
        self.actor = self.runtime.country('TNJ')

    def daily(self):
        hook = read(MOD / 'common/on_actions/terra_tnj_home_guard.txt')[0].one('on_daily').one('effect')
        self.runtime.execute(hook.children, self.scope)

    def test_daily_hook_returns_only_tnj_armies_abroad_to_owned_controlled_land(self):
        original = dict(self.runtime.armies)
        self.daily()
        for name, (owner, state) in self.runtime.armies.items():
            if owner == 'TNJ' and self.runtime.states[original[name][1]][0] != 'TNJ':
                self.assertEqual(('TNJ', 'TNJ'), self.runtime.states[state])
            else:
                self.assertEqual(original[name], (owner, state))

    def test_no_safe_home_does_not_rescue_guards_or_change_state_control(self):
        self.runtime.states[170] = self.runtime.states[172] = ('TNJ', 'CLM')
        original = dict(self.runtime.armies), dict(self.runtime.states)
        self.daily()
        self.assertEqual(original, (self.runtime.armies, self.runtime.states))

    def test_old_save_gets_rules_and_template_lock_without_recreating_troops(self):
        original_count = len(self.runtime.armies)
        manpower = self.actor.attrs['has_manpower']
        self.daily()
        self.assertFalse(self.actor.rules['can_be_called_to_war'])
        self.assertFalse(self.actor.rules['units_deployed_to_overlord'])
        self.assertTrue(self.actor.rules['can_not_declare_war'])
        self.assertEqual(original_count, len(self.runtime.armies))
        self.assertEqual(manpower, self.actor.attrs['has_manpower'])
        self.daily()
        self.assertEqual(1, sum(k == 'country_lock_all_division_template' for k, _ in self.actor.effects))

    def test_later_escape_is_repaired_again_without_touching_other_armies(self):
        self.daily()
        self.runtime.armies['guard_home'] = ('TNJ', 200)
        self.daily()
        self.assertEqual(('TNJ', 170), self.runtime.armies['guard_home'])
        self.assertEqual(('CLM', 200), self.runtime.armies['foreign_army'])

    def test_human_capitulated_and_other_countries_are_not_relocated(self):
        for case in ('human', 'capitulated', 'SGN', 'different_original'):
            with self.subTest(case=case):
                self.setUp()
                if case == 'human': self.actor.attrs['is_ai'] = False
                elif case == 'capitulated': self.actor.attrs['has_capitulated'] = True
                elif case == 'different_original': self.actor.attrs['original_tag'] = 'D01'
                else: self.scope = self.runtime.scope('SGN')
                original = dict(self.runtime.armies)
                self.daily()
                self.assertEqual(original, self.runtime.armies)
                self.assertFalse(self.actor.rules)

    def test_home_guard_ai_uses_a_valid_owned_state_predicate(self):
        profile = read(MOD / 'common/ai_strategy/terra_tnj_home_guard.txt')[0]
        self.assertTrue(self.runtime.check(profile.one('enable').children, self.scope))
        self.actor.owned_state_cores.clear()
        self.assertFalse(self.runtime.check(profile.one('enable').children, self.scope))


if __name__ == '__main__':
    unittest.main()
