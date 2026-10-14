"""Scenario regressions that execute the actual mod's scripted-effect AST.

Engine-provided facts (war state, army estimate, opinions, etc.) are inputs to
these tests. Passing does not prove that HOI4 supplies those facts/scopes as
expected; see docs/diplomacy playtest instructions for in-game verification.
"""
import unittest

from tools.validate_diplomacy import MOD, Runtime, Scope, read, walk


class NativeModelTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.scope = self.runtime.scope("SGN", "URS")
        self.runtime.country("CLM").attrs["exists"] = True
        self.actor = self.runtime.country("SGN")
        self.partner = self.runtime.country("URS")
        self.runtime.call("terra_dip_initialize_effect", self.scope)

    def variable(self, kind, target="URS"):
        return f"terra_dip_{kind}_{target}"

    def pair(self, trust=0, grief=0, score=0, target="URS", country=None):
        (country or self.actor).variables.update({
            self.variable("trust", target): trust,
            self.variable("grievance", target): grief,
            self.variable("score", target): score,
        })

    def test_initialization_keeps_existing_save_history(self):
        self.assertIn("terra_dip_initialized", self.actor.flags)
        self.pair(73, 61, -22)
        self.actor.variables["unrelated_story_variable"] = 123
        self.actor.flags.add("unrelated_story_flag")
        old = dict(self.actor.variables)
        old_flags = set(self.actor.flags)
        self.runtime.call("terra_dip_initialize_effect", self.scope)
        self.assertEqual(old, self.actor.variables)
        self.assertEqual(old_flags, self.actor.flags)

    def test_pair_change_clamps_both_limits(self):
        for trust, grief, dt, dg, expected in (
            (99, 98, 12, 12, (100, 100)),
            (1, 2, -12, -12, (0, 0)),
            (50, 50, 12, -5, (62, 45)),
        ):
            with self.subTest(trust=trust, grief=grief):
                self.pair(trust, grief)
                self.runtime.call("terra_dip_change_relation_effect", self.scope,
                                  PARTNER="FROM", TRUST=str(dt), GRIEVANCE=str(dg))
                self.assertEqual(expected, (self.actor.variables[self.variable("trust")], self.actor.variables[self.variable("grievance")]))

    def test_pair_memory_is_bilateral_and_target_specific(self):
        self.pair(20, 10)
        self.pair(40, 30, target="CLM")
        self.pair(70, 60, target="SGN", country=self.partner)
        partner_before = dict(self.partner.variables)
        other_before = (self.actor.variables[self.variable("trust", "CLM")], self.actor.variables[self.variable("grievance", "CLM")])
        self.runtime.call("terra_dip_change_relation_effect", self.scope,
                          PARTNER="FROM", TRUST="12", GRIEVANCE="-5")
        self.assertEqual((32, 5), (self.actor.variables[self.variable("trust")], self.actor.variables[self.variable("grievance")]))
        self.assertEqual(partner_before, self.partner.variables)
        self.assertEqual(other_before, (self.actor.variables[self.variable("trust", "CLM")], self.actor.variables[self.variable("grievance", "CLM")]))

    def test_dispatcher_preserves_current_scope_when_root_differs(self):
        current = self.runtime.country("CLM")
        self.runtime.call("terra_dip_initialize_effect", self.runtime.scope("CLM"))
        self.pair(10, 10, target="SGN", country=current)
        actor_before = dict(self.actor.variables)
        scope = Scope("CLM", "SGN", "URS", "URS")
        self.runtime.call("terra_dip_change_relation_effect", scope,
                          PARTNER="ROOT", TRUST="12", GRIEVANCE="-5")
        self.assertEqual((22, 5), (current.variables[self.variable("trust", "SGN")], current.variables[self.variable("grievance", "SGN")]))
        self.assertEqual(actor_before, self.actor.variables)

    def test_dynamic_country_pair_has_separate_memory(self):
        self.runtime.country("D01").attrs["exists"] = True
        self.pair(30, 30, target="D01")
        self.pair(70, 70)
        scope = self.runtime.scope("SGN", "D01")
        self.runtime.call("terra_dip_change_relation_effect", scope,
                          PARTNER="FROM", TRUST="12", GRIEVANCE="-5")
        self.assertEqual((42, 25), (self.actor.variables[self.variable("trust", "D01")], self.actor.variables[self.variable("grievance", "D01")]))
        self.assertEqual(70, self.actor.variables[self.variable("trust")])

    def test_refresh_uses_history_without_resetting_it(self):
        self.pair(73, 61, -22)
        self.runtime.call("terra_dip_refresh_pair_effect", self.scope, TARGET="URS")
        self.assertEqual(73, self.actor.variables[self.variable("trust")])
        self.assertEqual(61, self.actor.variables[self.variable("grievance")])
        self.assertTrue(-100 <= self.actor.variables[self.variable("score")] <= 100)

    def test_actual_scoring_respects_trust_and_grievance(self):
        scores = []
        for trust, grief in ((0, 90), (50, 50), (90, 0)):
            self.pair(trust, grief)
            self.runtime.call("terra_dip_refresh_pair_effect", self.scope, TARGET="URS")
            scores.append(self.actor.variables[self.variable("score")])
        self.assertLess(scores[0], scores[1])
        self.assertLess(scores[1], scores[2])

    def test_monthly_memory_decay_is_bounded_and_does_not_reset(self):
        self.pair(73, 61)
        self.runtime.call("terra_dip_monthly_pair_effect", self.scope, TARGET="URS")
        trust = self.actor.variables[self.variable("trust")]
        grief = self.actor.variables[self.variable("grievance")]
        self.assertTrue(0 < trust <= 73)
        self.assertTrue(0 < grief <= 61)
        self.pair(0, 0)
        self.runtime.call("terra_dip_monthly_pair_effect", self.scope, TARGET="URS")
        self.assertEqual((0, 0), (self.actor.variables[self.variable("trust")], self.actor.variables[self.variable("grievance")]))

    def test_participant_and_sovereign_boundaries(self):
        self.assertTrue(self.runtime.trigger("terra_dip_participant", self.scope))
        self.assertTrue(self.runtime.trigger("terra_dip_sovereign", self.scope))
        for attribute in ("is_subject",):
            with self.subTest(attribute=attribute):
                self.actor.attrs[attribute] = True
                self.assertFalse(self.runtime.trigger("terra_dip_sovereign", self.scope))
                self.actor.attrs[attribute] = False
        # Civil-war governments can seek outside support. Native war state,
        # subject status and pairwise fighting determine the actual actions.
        self.actor.attrs["has_civil_war"] = True
        self.assertTrue(self.runtime.trigger("terra_dip_sovereign", self.scope))
        self.actor.attrs["has_civil_war"] = False
        for attribute, value in (("exists", False), ("has_capitulated", True)):
            with self.subTest(attribute=attribute):
                previous = self.actor.attrs[attribute]
                self.actor.attrs[attribute] = value
                self.assertFalse(self.runtime.trigger("terra_dip_participant", self.scope))
                self.actor.attrs[attribute] = previous
        self.actor.owned_state_cores.clear()
        self.assertFalse(self.runtime.trigger("terra_dip_participant", self.scope))

    def test_uninhabited_and_seaborn_original_tags_remain_excluded(self):
        for tag in ("SST", "SEA"):
            with self.subTest(tag=tag):
                self.actor.attrs["original_tag"] = tag
                self.assertFalse(self.runtime.trigger("terra_dip_participant", self.scope))

    def war_ready(self):
        self.pair(trust=0, grief=95, score=-95)
        self.actor.flags.update({"terra_security_warned_URS", "terra_security_warning_mature_URS"})
        self.actor.variables["terra_dip_pressure"] = 0
        self.actor.attrs.update({"stability": 0.9, "war_support": 0.9, "has_manpower": 500000,
                                 "army_strength": 300, "num_divisions": 80,
                                 "num_of_factories": 100, "num_of_military_factories": 50,
                                 "industrial_capacity": 100})
        self.actor.relation("is_neighbor_of", "URS")
        self.actor.relation("has_wargoal_against", "URS")
        self.actor.relation("can_declare_war_on", "URS")
        self.actor.equipment["infantry_equipment"] = 2
        self.actor.stockpiles["infantry_equipment"] = 10000

    def test_war_policy_has_a_reachable_valid_baseline(self):
        self.war_ready()
        self.assertTrue(self.runtime.trigger("terra_dip_can_prepare_against", self.scope, TARGET="URS"))
        self.assertTrue(self.runtime.trigger("terra_dip_can_seek_war_against", self.scope, TARGET="URS"))

    def test_war_policy_blocks_expensive_or_illegal_wars(self):
        changes = (
            ("actor", "is_subject", True), ("target", "is_subject", True),
            ("actor", "has_war", True), ("actor", "stability", 0.1),
            ("actor", "surrender_progress", 0.7), ("actor", "has_manpower", 0),
            ("target", "exists", False), ("target", "has_capitulated", True),
        )
        for whose, attribute, value in changes:
            with self.subTest(whose=whose, attribute=attribute):
                self.setUp()
                self.war_ready()
                country = self.actor if whose == "actor" else self.partner
                country.attrs[attribute] = value
                self.assertFalse(self.runtime.trigger("terra_dip_can_seek_war_against", self.scope, TARGET="URS"))
        for relation in ("can_declare_war_on", "has_wargoal_against"):
            with self.subTest(missing=relation):
                self.setUp()
                self.war_ready()
                self.actor.relation(relation, "URS", False)
                strategy = next(node for node in read(MOD / "common/ai_strategy/terra_diplomacy.txt") if node.key == "terra_dip_legal_war_URS")
                self.assertFalse(self.runtime.check(strategy.one("enable").children, self.scope))
        self.setUp()
        self.war_ready()
        self.actor.stockpiles["infantry_equipment"] = 0
        self.assertFalse(self.runtime.trigger("terra_dip_can_seek_war_against", self.scope, TARGET="URS"))

    def test_civil_war_actor_cannot_start_another_war(self):
        self.war_ready()
        self.actor.attrs.update({"has_civil_war": True, "has_war": True})
        self.assertFalse(self.runtime.trigger("terra_dip_can_prepare_against", self.scope, TARGET="URS"))
        self.assertFalse(self.runtime.trigger("terra_dip_can_seek_war_against", self.scope, TARGET="URS"))

    def test_strength_estimate_compares_actor_against_target(self):
        self.war_ready()
        self.actor.attrs["army_strength"] = 300
        self.partner.attrs["army_strength"] = 100
        self.assertTrue(self.runtime.trigger("terra_dip_can_seek_war_against", self.scope, TARGET="URS"))
        self.actor.attrs["army_strength"] = 100
        self.partner.attrs["army_strength"] = 300
        self.assertFalse(self.runtime.trigger("terra_dip_can_seek_war_against", self.scope, TARGET="URS"))

    def test_friendly_blocs_and_ceasefire_prevent_war_preferences(self):
        for relation in ("is_in_faction_with", "has_non_aggression_pact_with"):
            with self.subTest(relation=relation):
                self.setUp()
                self.war_ready()
                self.actor.relation(relation, "URS")
                self.assertFalse(self.runtime.trigger("terra_dip_can_prepare_against", self.scope, TARGET="URS"))
                self.assertFalse(self.runtime.trigger("terra_dip_can_seek_war_against", self.scope, TARGET="URS"))

    def test_stronger_defending_coalition_blocks_war_preference(self):
        self.war_ready()
        protector = self.runtime.country("CLM")
        protector.relation("has_guaranteed", "URS")
        protector.attrs["army_strength"] = 500
        self.assertFalse(self.runtime.trigger("terra_dip_can_seek_war_against", self.scope, TARGET="URS"))
        protector.attrs["army_strength"] = 50
        self.assertTrue(self.runtime.trigger("terra_dip_can_seek_war_against", self.scope, TARGET="URS"))

    def test_absent_target_clears_stale_strategy_state_without_erasing_memory(self):
        self.pair(73, 61, 100)
        self.actor.flags.update({"terra_dip_partner_URS", "terra_dip_pact_URS"})
        self.partner.attrs["exists"] = False
        self.runtime.call("terra_dip_refresh_pair_effect", self.scope, TARGET="URS")
        self.assertEqual(0, self.actor.variables[self.variable("score")])
        self.assertEqual((73, 61), (self.actor.variables[self.variable("trust")], self.actor.variables[self.variable("grievance")]))
        self.assertNotIn("terra_dip_partner_URS", self.actor.flags)
        self.assertNotIn("terra_dip_pact_URS", self.actor.flags)
        self.partner.attrs["exists"] = True
        self.runtime.call("terra_dip_refresh_pair_effect", self.scope, TARGET="URS")
        self.assertEqual((73, 61), (self.actor.variables[self.variable("trust")], self.actor.variables[self.variable("grievance")]))

    def test_betrayal_is_recorded_once_after_partner_abandons_war(self):
        self.pair(80, 0)
        self.actor.flags.add("terra_dip_partner_URS")
        self.actor.attrs["has_war"] = True
        self.runtime.call("terra_dip_refresh_pair_effect", self.scope, TARGET="URS")
        self.assertEqual((45, 30), (self.actor.variables[self.variable("trust")], self.actor.variables[self.variable("grievance")]))
        self.runtime.call("terra_dip_refresh_pair_effect", self.scope, TARGET="URS")
        self.assertEqual((45, 30), (self.actor.variables[self.variable("trust")], self.actor.variables[self.variable("grievance")]))

    def test_help_hook_remembers_donor_once_per_pair(self):
        self.runtime.call("terra_dip_initialize_effect", self.runtime.scope("URS"))
        self.pair(10, 20, target="SGN", country=self.partner)
        hooks = next(node for node in read(MOD / "common/on_actions/terra_diplomacy.txt") if node.key == "on_actions")
        effect = hooks.one("on_lend_lease").one("effect")
        actor_before = dict(self.actor.variables)
        self.runtime.execute(effect.children, self.scope)
        self.assertEqual((15, 15), (self.partner.variables[self.variable("trust", "SGN")], self.partner.variables[self.variable("grievance", "SGN")]))
        self.assertEqual(actor_before, self.actor.variables)
        self.runtime.execute(effect.children, self.scope)
        self.assertEqual((15, 15), (self.partner.variables[self.variable("trust", "SGN")], self.partner.variables[self.variable("grievance", "SGN")]))

    def test_leaving_faction_blames_departing_country_only(self):
        self.runtime.call("terra_dip_initialize_effect", self.runtime.scope("URS"))
        self.pair(80, 0)
        self.pair(80, 0, target="SGN", country=self.partner)
        self.actor.flags.add("terra_dip_partner_URS")
        self.partner.flags.add("terra_dip_partner_SGN")
        self.actor.attrs["has_war"] = True
        self.partner.attrs["has_war"] = True
        hooks = next(node for node in read(MOD / "common/on_actions/terra_diplomacy.txt") if node.key == "on_actions")
        departure = hooks.one("on_leave_faction").one("effect")
        self.runtime.execute(departure.children, self.scope)
        self.assertEqual((80, 0), (self.actor.variables[self.variable("trust")], self.actor.variables[self.variable("grievance")]))
        self.assertNotIn("terra_dip_partner_URS", self.actor.flags)
        self.assertIn("terra_dip_partner_SGN", self.partner.flags)
        self.runtime.call("terra_dip_refresh_effect", self.runtime.scope("URS", "SGN"))
        self.assertEqual((45, 30), (self.partner.variables[self.variable("trust", "SGN")], self.partner.variables[self.variable("grievance", "SGN")]))
        self.runtime.call("terra_dip_refresh_effect", self.runtime.scope("URS", "SGN"))
        self.assertEqual((45, 30), (self.partner.variables[self.variable("trust", "SGN")], self.partner.variables[self.variable("grievance", "SGN")]))

    def test_join_and_call_hooks_share_one_directional_help_guard(self):
        self.runtime.call("terra_dip_initialize_effect", self.runtime.scope("URS"))
        self.pair(10, 20, target="SGN", country=self.partner)
        hooks = next(node for node in read(MOD / "common/on_actions/terra_diplomacy.txt") if node.key == "on_actions")
        old_actor = dict(self.actor.variables)
        self.runtime.execute(hooks.one("on_join_allies").one("effect").children, self.scope)
        self.runtime.execute(hooks.one("on_call_allies").one("effect").children, self.runtime.scope("URS", "SGN"))
        self.assertEqual((25, 15), (self.partner.variables[self.variable("trust", "SGN")], self.partner.variables[self.variable("grievance", "SGN")]))
        self.assertEqual(old_actor, self.actor.variables)

    def test_both_lend_lease_hooks_share_one_receipt_guard(self):
        self.runtime.call("terra_dip_initialize_effect", self.runtime.scope("URS"))
        self.pair(10, 20, target="SGN", country=self.partner)
        hooks = next(node for node in read(MOD / "common/on_actions/terra_diplomacy.txt") if node.key == "on_actions")
        old_actor = dict(self.actor.variables)
        for hook in ("on_lend_lease", "on_incoming_lend_lease"):
            self.runtime.execute(hooks.one(hook).one("effect").children, self.scope)
        self.assertEqual((15, 15), (self.partner.variables[self.variable("trust", "SGN")], self.partner.variables[self.variable("grievance", "SGN")]))
        self.assertEqual(old_actor, self.actor.variables)

    def test_strategy_enable_changes_with_new_history_and_current_war(self):
        profiles = {node.key: node for node in read(MOD / "common/ai_strategy/terra_diplomacy.txt")}
        self.pair(80, 0, 80)
        self.pair(80, 0, 80, target="CLM")
        goodwill = profiles["terra_dip_goodwill_URS"].one("enable").children
        other = profiles["terra_dip_goodwill_CLM"].one("enable").children
        self.assertTrue(self.runtime.check(goodwill, self.scope))
        self.assertTrue(self.runtime.check(other, self.scope))
        self.actor.relation("has_war_with", "URS")
        self.assertFalse(self.runtime.check(goodwill, self.scope))
        self.assertTrue(self.runtime.check(other, self.scope))
        self.actor.relation("has_war_with", "URS", False)
        self.pair(0, 90, -90)
        self.assertFalse(self.runtime.check(goodwill, self.scope))
        self.assertTrue(self.runtime.check(other, self.scope))


class NativeStructureTests(unittest.TestCase):
    def test_native_director_files_are_present_and_parse(self):
        for relative in (
            "common/scripted_effects/terra_diplomacy.txt",
            "common/scripted_triggers/terra_diplomacy.txt",
            "common/on_actions/terra_diplomacy.txt",
            "common/ai_strategy/terra_diplomacy.txt",
        ):
            with self.subTest(path=relative):
                nodes = read(MOD / relative)
                self.assertTrue(nodes)

    def test_no_stacking_or_unsupported_ai_strategy_removal(self):
        for folder in ("common/scripted_effects", "common/on_actions", "events"):
            for path in (MOD / folder).glob("*diplo*.txt"):
                for node in walk(read(path)):
                    self.assertNotIn(node.key, {"add_ai_strategy", "remove_ai_strategy", "has_war_goal_against", "declare_war_on", "annex_country"}, f"{path}:{node.line}")

    def test_strategies_deactivate_when_enable_conditions_change(self):
        definitions = read(MOD / "common/ai_strategy/terra_diplomacy.txt")
        self.assertTrue(definitions)
        for strategy in definitions:
            with self.subTest(strategy=strategy.key):
                self.assertEqual("yes", strategy.scalar("abort_when_not_enabled"))
                self.assertIsNotNone(strategy.one("enable"))
                for preference in strategy.fields("ai_strategy"):
                    if preference.scalar("type") != "avoid_starting_wars":
                        self.assertIsNotNone(preference.scalar("id"))

    def test_country_monthly_and_weekly_hooks_do_not_loop_over_world(self):
        nodes = read(MOD / "common/on_actions/terra_diplomacy.txt")
        hooks = next(node for node in nodes if node.key == "on_actions")
        for hook in hooks.children:
            if hook.key in {"on_monthly", "on_weekly"}:
                self.assertFalse(any(node.key == "every_country" for node in walk(hook.children)), hook.key)


if __name__ == "__main__":
    unittest.main()
