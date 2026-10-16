"""Actual-script scenarios for startup pact spam and common-war coalition formation.

Faction rosters and random branches are explicit fixtures, not engine verification.
"""
import unittest

from tools.validate_diplomacy import EventDelivery, MOD, Runtime, read


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
        partners = set(self.runtime.countries) - {"SST", "SEA"}
        self.assertEqual(partners, {n.key.removeprefix("terra_dip_restraint_") for n in positive})
        self.assertEqual(partners, {n.one("enable").one("terra_dip_pair_valid").scalar("TARGET") for n in negative})
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
                self.assertFalse(self.actor.rules.get("can_create_factions", False))

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


class SargonDefensiveCoalitionTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        for tag, name in (("BLV", "Bolivar"), ("CLM", "Columbia"), ("SGN", "Sargon")):
            country = self.runtime.country(tag)
            # Use the mod's actual starting parties, not generic monarchy fixtures.
            history = read(MOD / "history/countries" / f"{tag} - {name}.txt")
            country.attrs["has_government"] = next(n.scalar("ruling_party") for n in history if n.key == "set_politics")
            country.attrs["has_war"] = True
            self.runtime.call("terra_dip_initialize_effect", self.runtime.scope(tag))
            self.runtime.call("terra_state_initialize_effect", self.runtime.scope(tag))
        self.sargon = self.runtime.country("SGN")
        self.sargon.attrs.update({"is_ai": False, "is_in_faction": True, "is_faction_leader": True})
        for tag in ("BLV", "CLM"):
            self.runtime.country(tag).relation("has_war_with", "SGN")
            self.runtime.country(tag).relation("has_defensive_war_with", "SGN")
            self.sargon.relation("has_war_with", tag)
        self.runtime.country("BLV").opinions["CLM"] = -80
        self.runtime.country("CLM").opinions["BLV"] = -80
        self.scope = self.runtime.scope("BLV", "SGN")

    def test_real_starting_parties_have_explicit_join_defaults_without_fixture_permissions(self):
        self.assertEqual("junta", self.runtime.country("BLV").attrs["has_government"])
        self.assertEqual("classical_liberalism", self.runtime.country("CLM").attrs["has_government"])
        for tag in ("BLV", "CLM"):
            self.assertNotIn("can_join_factions", self.runtime.country(tag).rules)
            self.assertTrue(self.runtime.trigger("terra_coalition_actor", self.runtime.scope(tag)))
        for ideology, rules in self.runtime.ideology_rules.items():
            self.assertTrue(rules.get("can_join_factions"), ideology)

    def test_bolivar_and_columbia_defend_against_human_sargon_despite_ideological_dislike(self):
        for dlc in (False, True):
            with self.subTest(dlc=dlc):
                self.setUp()
                if dlc: self.runtime.dlcs.add("No Compromise, No Surrender")
                self.runtime.call("terra_coalition_weekly_effect", self.scope)
                self.assertEqual({"BLV": {"BLV", "CLM"}}, self.runtime.factions)
                self.assertNotIn("terra_coalition_generated", self.sargon.flags)
                self.assertTrue(self.sargon.attrs["is_faction_leader"])
                self.assertFalse(self.sargon.rules)

    def test_missing_real_ideology_permission_reproduces_the_old_bootstrap_block(self):
        self.runtime.ideology_rules["junta"].pop("can_join_factions")
        self.runtime.call("terra_coalition_weekly_effect", self.scope)
        self.assertFalse(self.runtime.factions)

    def test_dislike_exception_needs_defense_against_the_same_actual_enemy(self):
        self.runtime.country("CLM").relation("has_defensive_war_with", "SGN", False)
        self.runtime.country("CLM").attrs["has_defensive_war"] = True
        self.runtime.country("CLM").relation("has_defensive_war_with", "URS")
        self.assertFalse(self.runtime.trigger("terra_coalition_common_defensive_enemy", self.scope, TARGET="CLM"))
        self.runtime.call("terra_coalition_weekly_effect", self.scope)
        self.assertFalse(self.runtime.factions)

    def test_explicit_country_join_ban_overrides_ideology_default(self):
        self.runtime.country("CLM").rules["can_join_factions"] = False
        self.runtime.call("terra_coalition_weekly_effect", self.scope)
        self.assertFalse(self.runtime.factions)

    def test_war_hook_schedules_ai_defender_and_event_resets_root_before_forming(self):
        hooks = read(MOD / "common/on_actions/terra_diplomacy.txt")[0]
        effect = hooks.one("on_war_relation_added").one("effect")
        attacker_scope = self.runtime.scope("SGN", "BLV")
        self.runtime.execute(effect.children, attacker_scope)
        self.runtime.execute(effect.children, attacker_scope)
        self.assertEqual([EventDelivery("BLV", "SGN", "terra_coalition.1", "1")], self.runtime.deliveries)
        self.assertNotIn("terra_coalition_check_pending", self.sargon.flags)
        event = next(n for n in read(MOD / "events/terra_coalition_events.txt") if n.key == "country_event")
        self.runtime.execute(event.one("immediate").children, self.scope)
        self.assertEqual({"BLV": {"BLV", "CLM"}}, self.runtime.factions)
        self.assertNotIn("terra_coalition_check_pending", self.runtime.country("BLV").flags)

    def test_failed_native_creation_does_not_enroll_or_reward_and_retry_is_throttled(self):
        self.runtime.faction_creation_failures.add("BLV")
        self.runtime.call("terra_coalition_weekly_effect", self.scope)
        self.runtime.call("terra_coalition_weekly_effect", self.scope)
        self.assertFalse(self.runtime.factions)
        self.assertIn("terra_coalition_create_retry", self.runtime.country("BLV").flags)
        self.assertEqual(1, sum(key == "create_faction" for key, _ in self.runtime.country("BLV").effects))
        self.assertEqual(0, self.runtime.country("BLV").variables["terra_dip_trust_CLM"])
        self.assertNotIn("terra_coalition_member", self.runtime.country("CLM").flags)

    def test_failed_native_enrollment_does_not_grant_phantom_membership_or_trust(self):
        self.runtime.faction_join_failures.add("CLM")
        self.runtime.call("terra_coalition_form_pair_effect", self.scope, TARGET="CLM")
        self.runtime.call("terra_coalition_form_pair_effect", self.scope, TARGET="CLM")
        self.assertEqual({"BLV": {"BLV"}}, self.runtime.factions)
        self.assertIn("terra_coalition_join_failed_CLM", self.runtime.country("BLV").flags)
        self.assertFalse(self.runtime.country("CLM").attrs["is_in_faction"])
        self.assertNotIn("terra_coalition_member", self.runtime.country("CLM").flags)
        self.assertEqual(0, self.runtime.country("BLV").variables["terra_dip_trust_CLM"])
        self.assertEqual(1, sum(key == "add_to_faction" for key, _ in self.runtime.country("BLV").effects))
