"""Actual-script scenarios for startup pact spam and common-war coalition formation.

Faction rosters and random branches are explicit fixtures, not engine verification.
"""
import unittest

from tools.validate_diplomacy import MOD, Runtime, read


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        for tag in ("URS", "VCT", "CLM", "LTH"):
            scope = self.runtime.scope(tag)
            self.runtime.call("terra_dip_initialize_effect", scope)
            self.runtime.call("terra_state_initialize_effect", scope)
        self.scope = self.runtime.scope("URS", "VCT")
        self.actor = self.runtime.country("URS")
        self.partner = self.runtime.country("VCT")
        self.enemy = self.runtime.country("CLM")

    def profile(self, name, file):
        node = next(n for n in read(MOD / "common/ai_strategy" / file) if n.key == name)
        return self.runtime.check(node.one("enable").children, self.scope)

    def befriend(self):
        self.actor.variables.update({"terra_dip_trust_VCT": 60, "terra_dip_grievance_VCT": 0, "terra_dip_score_VCT": 65})
        self.actor.opinions["VCT"] = 50
        self.partner.opinions["URS"] = 50
        self.actor.relation("is_neighbor_of", "VCT")

    def shared_war(self, partner="VCT", enemy="CLM"):
        for tag in ("URS", partner):
            self.runtime.country(tag).attrs["has_war"] = True
            self.runtime.country(tag).relation("has_war_with", enemy)
            self.runtime.country(enemy).relation("has_war_with", tag)

    def test_startup_same_ideology_and_every_personality_do_not_offer_pacts(self):
        for personality in ("cautious", "guardian", "imperial", "pragmatic", "mercantile", "idealist"):
            with self.subTest(personality=personality):
                self.actor.flags.add("terra_dip_personality_" + personality)
                self.runtime.call("terra_dip_refresh_pair_effect", self.scope, TARGET="VCT")
                self.assertFalse(self.profile("terra_dip_restraint_VCT", "terra_diplomacy.txt"))
                self.assertTrue(self.profile("terra_dip_reject_generic_pact_VCT", "terra_diplomacy_policy.txt"))
                self.actor.flags.discard("terra_dip_personality_" + personality)

    def test_earned_friendship_only_offers_a_pact_for_a_specific_wartime_need(self):
        self.befriend()
        self.assertFalse(self.runtime.trigger("terra_dip_can_offer_restraint", self.scope, TARGET="VCT"))
        self.actor.attrs["has_war"] = True
        self.assertTrue(self.profile("terra_dip_restraint_VCT", "terra_diplomacy.txt"))
        self.assertFalse(self.profile("terra_dip_reject_generic_pact_VCT", "terra_diplomacy_policy.txt"))

    def test_pact_cannot_neutralize_claims_wargoals_warnings_or_common_war(self):
        self.befriend()
        self.actor.attrs["has_war"] = True
        for kind, target in (("has_wargoal_against", "VCT"), ("has_war_together_with", "VCT")):
            with self.subTest(kind=kind):
                self.actor.relation(kind, target)
                self.assertFalse(self.profile("terra_dip_restraint_VCT", "terra_diplomacy.txt"))
                self.actor.relation(kind, target, False)
        self.partner.relation("has_wargoal_against", "URS")
        self.assertFalse(self.profile("terra_dip_restraint_VCT", "terra_diplomacy.txt"))
        self.partner.relation("has_wargoal_against", "URS", False)
        self.partner.owned_state_cores[0].add("URS")
        self.assertFalse(self.profile("terra_dip_restraint_VCT", "terra_diplomacy.txt"))
        self.partner.owned_state_cores[0].clear()
        for flag in ("terra_security_warned_VCT", "terra_security_threat_VCT"):
            self.actor.flags.add(flag)
            self.assertFalse(self.profile("terra_dip_restraint_VCT", "terra_diplomacy.txt"))
            self.actor.flags.discard(flag)

    def test_all_registry_pact_profiles_use_the_same_eligibility_guard(self):
        positive = [n for n in read(MOD / "common/ai_strategy/terra_diplomacy.txt") if n.key.startswith("terra_dip_restraint_")]
        negative = read(MOD / "common/ai_strategy/terra_diplomacy_policy.txt")
        self.assertEqual(79, len(positive))
        self.assertEqual(79, len(negative))
        for node in positive:
            self.assertIsNotNone(node.one("enable").one("terra_dip_can_offer_restraint"))

    def test_neutral_startup_matrix_offers_no_pact_for_any_registered_country_pair(self):
        # Runtime discovers the actual registry across all country-tag files.
        tags = list(self.runtime.countries)
        for tag in tags:
            self.runtime.country(tag).attrs["has_government"] = "junta"
            self.runtime.call("terra_dip_initialize_effect", self.runtime.scope(tag))
            self.runtime.call("terra_state_initialize_effect", self.runtime.scope(tag))
            self.runtime.call("terra_state_refresh_personality_effect", self.runtime.scope(tag))
        for actor in tags:
            for target in tags:
                if actor == target:
                    continue
                scope = self.runtime.scope(actor, target)
                # Exercise the weekly score that exposed the original >9 bug.
                self.runtime.call("terra_dip_refresh_pair_effect", scope, TARGET=target)
                self.assertFalse(self.runtime.trigger("terra_dip_can_offer_restraint", scope, TARGET=target),
                                 f"Unexpected startup pact offer: {actor} -> {target}")

    def test_existing_pacts_are_preserved_and_not_repeatedly_requested(self):
        self.actor.relation("has_non_aggression_pact_with", "VCT")
        self.assertFalse(self.profile("terra_dip_restraint_VCT", "terra_diplomacy.txt"))
        self.assertFalse(self.profile("terra_dip_reject_generic_pact_VCT", "terra_diplomacy_policy.txt"))
        self.runtime.call("terra_coalition_weekly_effect", self.scope)
        self.assertIn("VCT", self.actor.relations["has_non_aggression_pact_with"])

    def test_peaceful_startup_and_different_enemies_cannot_create_a_faction(self):
        self.runtime.call("terra_coalition_weekly_effect", self.scope)
        self.assertFalse(self.runtime.factions)
        self.actor.attrs["has_war"] = self.partner.attrs["has_war"] = True
        self.actor.relation("has_war_with", "CLM")
        self.enemy.relation("has_war_with", "URS")
        self.partner.relation("has_war_with", "LTH")
        self.runtime.country("LTH").relation("has_war_with", "VCT")
        self.runtime.call("terra_coalition_weekly_effect", self.scope)
        self.assertFalse(self.runtime.factions)

    def test_shared_enemy_creates_a_real_two_country_faction_once(self):
        self.shared_war()
        wars = {tag: set(self.runtime.country(tag).relations.get("has_war_with", set())) for tag in ("URS", "VCT", "CLM")}
        self.runtime.call("terra_coalition_form_pair_effect", self.scope, TARGET="VCT")
        self.assertEqual({"URS": {"URS", "VCT"}}, self.runtime.factions)
        self.assertTrue(self.actor.attrs["is_faction_leader"])
        self.assertTrue(self.partner.attrs["is_in_faction"])
        self.assertIn("terra_coalition_generated", self.actor.flags)
        self.runtime.call("terra_coalition_form_pair_effect", self.scope, TARGET="VCT")
        self.assertEqual(1, sum(k == "create_faction" for k, _ in self.actor.effects))
        self.assertEqual(1, sum(k == "add_to_faction" for k, _ in self.actor.effects))
        self.assertEqual(wars, {tag: set(self.runtime.country(tag).relations.get("has_war_with", set())) for tag in wars})

    def test_new_common_enemy_partner_can_join_generated_faction(self):
        self.shared_war()
        self.runtime.call("terra_coalition_form_pair_effect", self.scope, TARGET="VCT")
        self.shared_war(partner="LTH")
        self.runtime.call("terra_coalition_form_pair_effect", self.scope, TARGET="LTH")
        self.assertEqual({"URS", "VCT", "LTH"}, self.runtime.factions["URS"])
        self.assertEqual(1, sum(k == "create_faction" for k, _ in self.actor.effects))

    def test_humans_subjects_foreign_factions_and_join_bans_are_never_enrolled(self):
        for change in ("human_actor", "human_partner", "subject", "existing_faction", "join_ban", "cooldown"):
            with self.subTest(change=change):
                self.setUp()
                self.shared_war()
                if change == "human_actor": self.actor.attrs["is_ai"] = False
                elif change == "human_partner": self.partner.attrs["is_ai"] = False
                elif change == "subject": self.partner.attrs["is_subject"] = True
                elif change == "existing_faction": self.partner.attrs["is_in_faction"] = True
                elif change == "join_ban": self.partner.rules["can_join_factions"] = False
                else: self.partner.flags.add("terra_coalition_rejoin_cooldown")
                self.runtime.call("terra_coalition_form_pair_effect", self.scope, TARGET="VCT")
                self.assertFalse(self.runtime.factions)
                self.assertFalse(self.actor.rules["can_create_factions"])

    def test_existing_story_faction_leader_does_not_enroll_outsiders(self):
        self.shared_war()
        self.actor.attrs.update({"is_in_faction": True, "is_faction_leader": True})
        self.runtime.call("terra_coalition_form_pair_effect", self.scope, TARGET="VCT")
        self.assertFalse(self.partner.attrs["is_in_faction"])
        self.assertFalse(any(k == "add_to_faction" for k, _ in self.actor.effects))

    def test_names_vary_and_template_is_used_with_faction_dlc(self):
        names = []
        for index in (0, 1, 2):
            self.setUp()
            self.shared_war()
            self.runtime.random_choice_index = index
            self.runtime.dlcs.add("No Compromise, No Surrender")
            self.runtime.call("terra_coalition_form_pair_effect", self.scope, TARGET="VCT")
            creations = [node for key, node in self.actor.effects if key == "create_faction_from_template"]
            self.assertEqual(1, len(creations))
            names.append(creations[0].scalar("name"))
            self.assertFalse(any(k == "create_faction" for k, _ in self.actor.effects))
        self.assertEqual(3, len(set(names)))

    def test_enemy_disappearing_stops_new_membership(self):
        self.shared_war()
        self.enemy.attrs["has_capitulated"] = True
        self.runtime.call("terra_coalition_form_pair_effect", self.scope, TARGET="VCT")
        self.assertFalse(self.runtime.factions)
