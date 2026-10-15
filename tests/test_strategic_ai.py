"""Regression scenarios over native all-country strategic script ASTs.

Army estimates, logistics, leaders and country scopes are explicit inputs.
Passing tests are not HOI4 AI, scheduler, save or gameplay verification.
"""
import unittest

from tools.validate_diplomacy import EventDelivery, MOD, Runtime, Scope, read, walk


class StrategicFixture(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        for tag in ("SGN", "URS", "CLM"):
            self.runtime.call("terra_dip_initialize_effect", self.runtime.scope(tag))
        self.scope = self.runtime.scope("SGN", "URS")
        self.actor = self.runtime.country("SGN")
        self.partner = self.runtime.country("URS")
        self.third = self.runtime.country("CLM")

    def profile(self, name, file):
        definition = next(node for node in read(MOD / "common/ai_strategy" / file) if node.key == name)
        return self.runtime.check(definition.one("enable").children, self.scope)


class WarLogisticsTests(StrategicFixture):
    def test_supply_emergency_is_gated_by_unlocked_logistics_and_army_size(self):
        self.actor.stockpiles.update({"infantry_equipment": 4000, "train_equipment": 0, "motorized_equipment": 0})
        self.actor.attrs.update({"has_manpower": 50000, "num_divisions": 25})
        self.assertFalse(self.runtime.trigger("terra_war_supply_emergency", self.scope))
        self.actor.technologies.add("basic_train")
        self.assertTrue(self.runtime.trigger("terra_war_supply_emergency", self.scope))
        self.actor.stockpiles["train_equipment"] = 5
        self.assertFalse(self.runtime.trigger("terra_war_supply_emergency", self.scope))
        self.actor.technologies.add("motorised_infantry")
        self.assertTrue(self.runtime.trigger("terra_war_supply_emergency", self.scope))
        self.actor.attrs["num_divisions"] = 24
        self.assertFalse(self.runtime.trigger("terra_war_supply_emergency", self.scope))
        self.actor.attrs["num_divisions"] = 25
        self.actor.stockpiles["motorized_equipment"] = 100
        self.assertFalse(self.runtime.trigger("terra_war_supply_emergency", self.scope))
        self.actor.stockpiles["infantry_equipment"] = 399
        self.assertTrue(self.runtime.trigger("terra_war_supply_emergency", self.scope))

    def test_front_profiles_require_actual_war_and_switch_with_deficits(self):
        file = "terra_war_director.txt"
        self.assertFalse(self.profile("terra_war_conserve_front", file))
        self.assertFalse(self.profile("terra_war_prepared_front", file))
        self.actor.attrs["has_war"] = True
        self.actor.stockpiles["infantry_equipment"] = 100
        self.assertTrue(self.profile("terra_war_conserve_front", file))
        self.assertFalse(self.profile("terra_war_prepared_front", file))
        self.actor.stockpiles["infantry_equipment"] = 10000
        self.assertFalse(self.profile("terra_war_conserve_front", file))
        self.assertTrue(self.profile("terra_war_prepared_front", file))
        self.actor.variables["terra_state_fatigue"] = 80
        self.assertTrue(self.profile("terra_war_conserve_front", file))
        self.assertFalse(self.profile("terra_war_prepared_front", file))
        self.actor.attrs["is_ai"] = False
        self.assertFalse(self.profile("terra_war_conserve_front", file))

    def test_fatigue_domestic_pressure_and_defeat_block_sustained_operations(self):
        self.assertTrue(self.runtime.trigger("terra_war_can_sustain_operations", self.scope))
        for variable, blocked in (("terra_state_fatigue", 55), ("terra_state_domestic_pressure", 60), ("terra_state_defeat_memory", 60)):
            with self.subTest(variable=variable):
                self.actor.variables[variable] = blocked
                self.assertFalse(self.runtime.trigger("terra_war_can_sustain_operations", self.scope))
                self.actor.variables[variable] = 0
        self.assertTrue(self.runtime.trigger("terra_war_can_sustain_operations", self.scope))

    def test_nearby_enemy_prevents_sending_surplus_to_allied_front(self):
        self.assertTrue(self.runtime.trigger("terra_war_can_spare_allied_force", self.scope))
        self.actor.relation("has_war_with", "URS")
        self.partner.relation("is_neighbor_of", "SGN")
        self.assertFalse(self.runtime.trigger("terra_war_can_spare_allied_force", self.scope))
        self.partner.attrs["has_capitulated"] = True
        self.assertTrue(self.runtime.trigger("terra_war_can_spare_allied_force", self.scope))

    def test_subject_duty_survives_fatigue_without_activating_costly_refusal(self):
        self.actor.attrs.update({"is_subject": True, "stability": 0.1})
        self.actor.relation("is_subject_of", "URS")
        self.partner.attrs["has_war"] = True
        self.actor.variables.update({"terra_state_fatigue": 95, "terra_state_domestic_pressure": 95, "terra_dip_pressure": 95})
        self.assertFalse(self.runtime.trigger("terra_war_can_sustain_operations", self.scope))
        self.assertTrue(self.profile("terra_dip_subject_duty_URS", "terra_diplomacy.txt"))
        self.assertFalse(self.profile("terra_dip_decline_costly_call_URS", "terra_diplomacy.txt"))

    def test_legacy_remote_requests_stop_under_exhaustion_but_subject_call_duty_stays(self):
        self.runtime.call("terra_state_initialize_effect", self.scope)
        self.actor.attrs.update({"is_subject": True, "is_in_faction": True, "has_war": True})
        self.partner.attrs["has_war"] = True
        self.actor.relation("is_subject_of", "URS")
        self.actor.relation("has_war_together_with", "URS")
        self.assertTrue(self.profile("terra_subject_remote_support_URS", "terra_remote_fronts.txt"))
        self.assertTrue(self.profile("terra_ai_faction_remote_fronts", "terra_ai_warfare.txt"))
        self.actor.variables["terra_state_fatigue"] = 95
        self.assertFalse(self.profile("terra_subject_remote_support_URS", "terra_remote_fronts.txt"))
        self.assertFalse(self.profile("terra_ai_faction_remote_fronts", "terra_ai_warfare.txt"))
        # An exhausted puppet still answers a new overlord call. Already
        # sharing that war would correctly make the call profile unnecessary.
        self.actor.relation("has_war_together_with", "URS", False)
        self.assertTrue(self.profile("terra_state_subject_loyalty_URS", "terra_strategic_state.txt"))
        loyalty = next(node for node in read(MOD / "common/ai_strategy/terra_strategic_state.txt") if node.key == "terra_state_subject_loyalty_URS")
        call = next(node for node in loyalty.fields("ai_strategy") if node.scalar("target") == "call_allies")
        self.assertEqual("1000", call.scalar("value"))


class PersistentStateTests(StrategicFixture):
    def setUp(self):
        super().setUp()
        for tag in ("SGN", "URS", "CLM"):
            self.runtime.call("terra_state_initialize_effect", self.runtime.scope(tag))

    def test_initialization_is_idempotent_and_preserves_save_memory(self):
        self.actor.variables.update({"terra_state_fatigue": 71, "terra_state_defeat_memory": 82, "terra_state_reputation": 24})
        self.actor.flags.add("user_story_flag")
        before = dict(self.actor.variables)
        flags = set(self.actor.flags)
        self.runtime.call("terra_state_initialize_effect", self.scope)
        self.assertEqual(before, self.actor.variables)
        self.assertEqual(flags, self.actor.flags)

    def test_wartime_fatigue_accumulates_and_stable_peace_recovers(self):
        self.actor.variables.update({"terra_state_fatigue": 99, "terra_state_defeat_memory": 80, "terra_state_reputation": 49})
        self.actor.attrs.update({"has_war": True, "has_offensive_war": True, "has_civil_war": True})
        self.runtime.call("terra_state_monthly_effect", self.scope)
        self.assertEqual(100, self.actor.variables["terra_state_fatigue"])
        self.assertEqual(80, self.actor.variables["terra_state_defeat_memory"])
        self.actor.attrs.update({"has_war": False, "has_offensive_war": False, "has_civil_war": False})
        self.runtime.call("terra_state_monthly_effect", self.scope)
        self.assertEqual(96, self.actor.variables["terra_state_fatigue"])
        self.assertEqual(79, self.actor.variables["terra_state_defeat_memory"])
        self.assertEqual(50, self.actor.variables["terra_state_reputation"])
        self.runtime.call("terra_state_monthly_effect", self.scope)
        self.assertEqual(50, self.actor.variables["terra_state_reputation"])

    def test_capitulated_loser_records_defeat_once_without_harming_winner(self):
        self.actor.attrs["has_capitulated"] = True
        self.assertFalse(self.runtime.trigger("terra_state_ready", self.scope))
        self.assertTrue(self.runtime.trigger("terra_state_recordable", self.scope))
        winner_before = dict(self.partner.variables)
        hooks = next(node for node in read(MOD / "common/on_actions/terra_diplomacy.txt") if node.key == "on_actions")
        callback = hooks.one("on_capitulation").one("effect")
        self.runtime.execute(callback.children, self.scope)
        self.assertEqual((40, 20), (self.actor.variables["terra_state_defeat_memory"], self.actor.variables["terra_state_fatigue"]))
        self.assertIn("terra_state_goal_recovery", self.actor.flags)
        self.runtime.execute(callback.children, self.scope)
        self.assertEqual((40, 20), (self.actor.variables["terra_state_defeat_memory"], self.actor.variables["terra_state_fatigue"]))
        self.assertEqual(winner_before, self.partner.variables)

    def test_fulfillment_and_breach_change_reputation_once_per_cooldown(self):
        self.runtime.call("terra_state_record_fulfillment_effect", self.scope)
        self.runtime.call("terra_state_record_fulfillment_effect", self.scope)
        self.assertEqual(53, self.actor.variables["terra_state_reputation"])
        self.runtime.call("terra_state_record_breach_effect", self.scope)
        self.runtime.call("terra_state_record_breach_effect", self.scope)
        self.assertEqual(38, self.actor.variables["terra_state_reputation"])
        self.assertIn("terra_dip_oathbreaker", self.actor.flags)
        self.actor.flags.discard("terra_state_recent_fulfillment")
        self.actor.variables["terra_state_reputation"] = 99
        self.runtime.call("terra_state_record_fulfillment_effect", self.scope)
        self.assertEqual(100, self.actor.variables["terra_state_reputation"])

    def test_pressure_recomputes_and_is_bounded_under_stress(self):
        self.actor.attrs.update({"has_war": True, "has_civil_war": True, "stability": 0.1, "war_support": 0.1,
                                 "has_manpower": 0, "surrender_progress": 0.5, "num_of_civilian_factories": 0})
        self.actor.stockpiles["infantry_equipment"] = 0
        self.runtime.call("terra_state_refresh_domestic_pressure_effect", self.scope)
        self.assertEqual(100, self.actor.variables["terra_state_domestic_pressure"])
        self.actor.attrs.update({"has_war": False, "has_civil_war": False, "stability": 0.9, "war_support": 0.9,
                                 "has_manpower": 200000, "surrender_progress": 0, "num_of_civilian_factories": 20})
        self.actor.stockpiles["infantry_equipment"] = 10000
        self.runtime.call("terra_state_refresh_domestic_pressure_effect", self.scope)
        self.assertEqual(0, self.actor.variables["terra_state_domestic_pressure"])
        self.assertNotIn("terra_state_fatigue_pressure", self.actor.variables)

    def test_ruler_change_replaces_personality_without_resetting_history(self):
        self.partner.ruling_leader = "URS_ivan"
        self.runtime.call("terra_state_refresh_personality_effect", self.runtime.scope("URS"))
        self.assertIn("terra_dip_personality_imperial", self.partner.flags)
        self.partner.variables["terra_dip_trust_SGN"] = 78
        self.partner.ruling_leader = "new_ruler"
        self.partner.attrs["has_government"] = "social_democracy"
        self.runtime.call("terra_state_refresh_personality_effect", self.runtime.scope("URS"))
        personalities = {flag for flag in self.partner.flags if flag.startswith("terra_dip_personality_")}
        self.assertEqual({"terra_dip_personality_idealist"}, personalities)
        self.assertEqual(78, self.partner.variables["terra_dip_trust_SGN"])

    def test_dynamic_country_state_is_separate_and_original_exclusions_apply(self):
        scope = self.runtime.scope("D01", "SGN")
        country = self.runtime.country("D01")
        country.attrs["original_tag"] = "URS"
        self.runtime.call("terra_dip_initialize_effect", scope)
        self.runtime.call("terra_state_initialize_effect", scope)
        self.assertTrue(self.runtime.trigger("terra_state_ready", scope))
        self.runtime.call("terra_state_record_defeat_effect", scope)
        self.assertEqual(40, country.variables["terra_state_defeat_memory"])
        self.assertEqual(0, self.actor.variables["terra_state_defeat_memory"])
        for original in ("SST", "SEA"):
            country.attrs["original_tag"] = original
            self.assertFalse(self.runtime.trigger("terra_state_recordable", scope))

    def test_recovery_goal_hysteresis_keeps_exactly_one_goal(self):
        goals = {"terra_state_goal_security", "terra_state_goal_commerce", "terra_state_goal_revision", "terra_state_goal_recovery"}
        self.actor.flags.update(goals)
        for fatigue, expected in ((60, "terra_state_goal_recovery"), (40, "terra_state_goal_recovery"), (30, "terra_state_goal_security")):
            with self.subTest(fatigue=fatigue):
                self.actor.variables["terra_state_fatigue"] = fatigue
                self.runtime.call("terra_state_refresh_goals_effect", self.scope)
                self.assertEqual({expected}, goals & self.actor.flags)


class SecurityTests(StrategicFixture):
    def setUp(self):
        super().setUp()
        for tag in ("SGN", "URS", "CLM"):
            self.runtime.call("terra_state_initialize_effect", self.runtime.scope(tag))
        self.actor.variables.update({"terra_dip_grievance_URS": 80, "terra_dip_score_URS": -80})
        self.actor.relation("is_neighbor_of", "URS")

    def warning(self):
        self.runtime.call("terra_security_refresh_warning_pair_effect", self.scope, TARGET="URS")

    def test_war_preparation_requires_actual_warning_and_elapsed_pending_period(self):
        self.assertTrue(self.runtime.trigger("terra_security_can_warn", self.scope, TARGET="URS"))
        self.assertFalse(self.runtime.trigger("terra_dip_can_prepare_against", self.scope, TARGET="URS"))
        self.warning()
        self.assertIn("terra_security_warned_URS", self.actor.flags)
        self.assertIn("terra_security_warning_pending_URS", self.actor.flags)
        self.assertFalse(self.runtime.trigger("terra_security_warning_ready", self.scope, TARGET="URS"))
        self.warning()
        self.assertNotIn("terra_security_warning_mature_URS", self.actor.flags)
        # Fixture represents the native 60-day flag having expired, not a
        # simulated engine timer. No warning can mature while it is present.
        self.actor.flags.discard("terra_security_warning_pending_URS")
        self.warning()
        self.assertTrue(self.runtime.trigger("terra_security_warning_ready", self.scope, TARGET="URS"))
        self.assertTrue(self.runtime.trigger("terra_dip_can_prepare_against", self.scope, TARGET="URS"))

    def test_backdown_clears_escalation_but_keeps_warning_cooldown(self):
        self.warning()
        self.actor.relation("has_non_aggression_pact_with", "URS")
        self.warning()
        self.assertFalse(any(flag in self.actor.flags for flag in ("terra_security_warned_URS", "terra_security_warning_pending_URS", "terra_security_warning_mature_URS")))
        self.assertIn("terra_security_warning_cooldown_URS", self.actor.flags)
        self.actor.relation("has_non_aggression_pact_with", "URS", False)
        self.warning()
        self.assertNotIn("terra_security_warned_URS", self.actor.flags)
        self.actor.flags.discard("terra_security_warning_cooldown_URS")
        self.warning()
        self.assertIn("terra_security_warning_pending_URS", self.actor.flags)
        self.actor.variables["terra_state_fatigue"] = 90
        self.warning()
        self.assertNotIn("terra_security_warned_URS", self.actor.flags)

    def test_human_notice_cooldown_delays_warning_without_silent_maturity(self):
        self.partner.attrs["is_ai"] = False
        self.partner.flags.add("terra_security_notice_cooldown")
        self.warning()
        self.assertNotIn("terra_security_warned_URS", self.actor.flags)
        self.assertNotIn("terra_security_warning_mature_URS", self.actor.flags)
        self.assertFalse(self.runtime.deliveries)
        self.partner.flags.discard("terra_security_notice_cooldown")
        self.warning()
        self.assertEqual([EventDelivery("URS", "SGN", "terra_security.1", "0")], self.runtime.deliveries)
        self.assertIn("terra_security_warning_pending_URS", self.actor.flags)

    def test_shared_threat_requires_two_observers_and_current_same_danger(self):
        self.partner.flags.add("terra_dip_recent_aggressor")
        self.third.relation("is_neighbor_of", "URS")
        self.third.variables.update({"terra_dip_grievance_URS": 80, "terra_dip_score_URS": -80})
        self.runtime.call("terra_security_refresh_threat_pair_effect", self.scope, TARGET="URS")
        self.assertFalse(self.runtime.trigger("terra_security_has_shared_threat", self.scope, PARTNER="CLM"))
        self.runtime.call("terra_security_refresh_threat_pair_effect", self.runtime.scope("CLM"), TARGET="URS")
        self.assertTrue(self.runtime.trigger("terra_security_has_shared_threat", self.scope, PARTNER="CLM"))
        self.assertTrue(self.runtime.trigger("terra_security_can_coordinate", self.scope, PARTNER="CLM"))
        self.partner.flags.discard("terra_dip_recent_aggressor")
        self.assertFalse(self.runtime.trigger("terra_security_has_shared_threat", self.scope, PARTNER="CLM"))

    def test_native_intelligence_and_legacy_crypto_adjust_estimated_margin(self):
        self.actor.attrs["army_strength"] = 145
        self.partner.attrs["army_strength"] = 100
        self.assertFalse(self.runtime.trigger("terra_security_confident_advantage", self.scope, TARGET="URS"))
        self.actor.technologies.add("advanced_decryption")
        self.runtime.call("terra_security_refresh_intel_pair_effect", self.scope, TARGET="URS")
        self.assertIn("terra_security_intel_high_URS", self.actor.flags)
        self.assertTrue(self.runtime.trigger("terra_security_confident_advantage", self.scope, TARGET="URS"))
        self.partner.technologies.add("advanced_encryption")
        self.runtime.call("terra_security_refresh_intel_pair_effect", self.scope, TARGET="URS")
        self.assertIn("terra_security_intel_low_URS", self.actor.flags)
        self.assertFalse(self.runtime.trigger("terra_security_confident_advantage", self.scope, TARGET="URS"))
        self.runtime.dlcs.add("La Resistance")
        self.actor.intelligence["URS"] = {"army_intel": 0.7}
        self.runtime.call("terra_security_refresh_intel_pair_effect", self.scope, TARGET="URS")
        self.assertIn("terra_security_intel_high_URS", self.actor.flags)
        self.actor.intelligence["URS"]["army_intel"] = 0.5
        self.runtime.call("terra_security_refresh_intel_pair_effect", self.scope, TARGET="URS")
        self.assertIn("terra_security_intel_medium_URS", self.actor.flags)
        self.assertFalse(self.runtime.trigger("terra_security_confident_advantage", self.scope, TARGET="URS"))

    def test_unanswered_coordination_defaults_to_neutral_decline(self):
        event = next(node for node in read(MOD / "events/terra_security_events.txt") if node.key == "country_event" and node.scalar("id") == "terra_security.10")
        default = event.fields("option")[0]
        self.assertEqual("terra_security.10.b", default.scalar("name"))
        self.assertEqual(["name"], [node.key for node in default.children])


class CommitmentTests(StrategicFixture):
    def setUp(self):
        super().setUp()
        for tag in ("SGN", "URS", "CLM"):
            self.runtime.call("terra_state_initialize_effect", self.runtime.scope(tag))
        self.actor.stockpiles["infantry_equipment"] = 1000
        self.partner.stockpiles["infantry_equipment"] = 200

    def sign_aid(self, small=False):
        self.runtime.call("terra_contract_offer_aid_effect", self.scope)
        self.assertTrue(self.runtime.trigger("terra_contract_aid_donor_from", self.scope))
        self.assertTrue(self.runtime.trigger("terra_contract_aid_client_from", self.runtime.scope("URS", "SGN")))
        self.runtime.call("terra_contract_sign_aid_effect", self.scope, MIN_STOCK="149" if small else "299", SMALL="yes" if small else "no")

    def stocks(self):
        return self.actor.stockpiles["infantry_equipment"], self.partner.stockpiles["infantry_equipment"]

    def test_signature_reserves_one_promise_without_creating_or_shipping_equipment(self):
        self.sign_aid()
        self.assertEqual((1000, 200), self.stocks())
        self.assertIn("terra_contract_aid_donor_URS", self.actor.flags)
        self.assertIn("terra_contract_aid_receiver_SGN", self.partner.flags)
        self.assertIn("terra_contract_aid_wait_URS", self.actor.flags)
        self.assertNotIn("terra_contract_pending", self.actor.flags)
        self.assertNotIn("terra_contract_pending", self.partner.flags)
        self.assertFalse(self.runtime.trigger("terra_contract_free", self.scope))
        self.runtime.call("terra_contract_weekly_effect", self.scope)
        self.assertEqual((1000, 200), self.stocks())

    def test_due_shipments_conserve_inventory_and_complete_exactly_once(self):
        for small, amount in ((False, 300), (True, 150)):
            with self.subTest(amount=amount):
                self.setUp()
                self.sign_aid(small)
                self.runtime.call("terra_contract_due_aid_effect", self.scope)
                self.assertEqual((1000 - amount, 200 + amount), self.stocks())
                self.assertEqual(1200, sum(self.stocks()))
                self.assertEqual(53, self.actor.variables["terra_state_reputation"])
                self.assertEqual(12, self.partner.variables["terra_dip_trust_SGN"])
                self.assertNotIn("terra_contract_active", self.actor.flags)
                self.assertNotIn("terra_contract_active", self.partner.flags)
                for effect in ("terra_contract_due_aid_effect", "terra_contract_aid_deadline_effect", "terra_contract_weekly_effect"):
                    self.runtime.call(effect, self.scope)
                self.assertEqual((1000 - amount, 200 + amount), self.stocks())
                self.assertEqual(53, self.actor.variables["terra_state_reputation"])
                self.assertEqual(1, sum(key == "send_equipment" for key, node in self.actor.effects))

    def test_empty_due_stock_enters_grace_then_defaults_once_without_free_delivery(self):
        self.sign_aid()
        self.actor.stockpiles["infantry_equipment"] = 100
        self.runtime.call("terra_contract_due_aid_effect", self.scope)
        self.assertEqual((100, 200), self.stocks())
        self.assertIn("terra_contract_aid_due_URS", self.actor.flags)
        self.assertIn("terra_contract_aid_grace_URS", self.actor.flags)
        self.runtime.call("terra_contract_weekly_effect", self.scope)
        self.assertEqual(50, self.actor.variables["terra_state_reputation"])
        self.runtime.call("terra_contract_aid_deadline_effect", self.scope)
        self.assertEqual(35, self.actor.variables["terra_state_reputation"])
        self.assertEqual(15, self.partner.variables["terra_dip_grievance_SGN"])
        self.assertNotIn("terra_contract_active", self.actor.flags)
        self.assertNotIn("terra_contract_active", self.partner.flags)
        self.runtime.call("terra_contract_aid_deadline_effect", self.scope)
        self.runtime.call("terra_contract_weekly_effect", self.scope)
        self.assertEqual(35, self.actor.variables["terra_state_reputation"])
        self.assertEqual((100, 200), self.stocks())
        self.assertFalse(any(key == "send_equipment" for key, node in self.actor.effects))

    def test_recovered_inventory_during_grace_fulfills_and_late_callback_is_harmless(self):
        self.sign_aid()
        self.actor.stockpiles["infantry_equipment"] = 100
        self.runtime.call("terra_contract_due_aid_effect", self.scope)
        self.actor.stockpiles["infantry_equipment"] = 400
        self.runtime.call("terra_contract_weekly_effect", self.scope)
        self.assertEqual((100, 500), self.stocks())
        self.assertEqual(53, self.actor.variables["terra_state_reputation"])
        self.runtime.call("terra_contract_aid_deadline_effect", self.scope)
        self.assertEqual((100, 500), self.stocks())
        self.assertEqual(53, self.actor.variables["terra_state_reputation"])

    def test_unrelated_partner_cannot_sign_or_cancel_somebody_elses_pending_pair(self):
        self.runtime.call("terra_contract_offer_aid_effect", self.scope)
        wrong_pair = self.runtime.scope("SGN", "CLM")
        self.assertFalse(self.runtime.trigger("terra_contract_aid_donor_from", wrong_pair))
        self.runtime.call("terra_contract_sign_aid_effect", wrong_pair, MIN_STOCK="299", SMALL="no")
        self.assertIn("terra_contract_pending_with_URS", self.actor.flags)
        self.assertIn("terra_contract_pending_with_SGN", self.partner.flags)
        self.assertNotIn("terra_contract_active", self.actor.flags)
        self.assertEqual((1000, 200), self.stocks())

    def test_inventory_recovered_after_grace_cannot_be_delivered_by_weekly_fallback(self):
        self.sign_aid()
        self.actor.stockpiles["infantry_equipment"] = 100
        self.runtime.call("terra_contract_due_aid_effect", self.scope)
        # Explicit input represents expired native grace; this runner has no clock.
        self.actor.flags.discard("terra_contract_aid_grace_URS")
        self.actor.stockpiles["infantry_equipment"] = 400
        self.runtime.call("terra_contract_weekly_effect", self.scope)
        self.assertEqual((400, 200), self.stocks())
        self.assertEqual(35, self.actor.variables["terra_state_reputation"])
        self.assertNotIn("terra_contract_active", self.actor.flags)
        self.assertFalse(any(key == "send_equipment" for key, _ in self.actor.effects))

    def test_new_defensive_war_after_term_expiry_does_not_extend_the_contract(self):
        self.actor.flags.update({"terra_contract_active", "terra_contract_defender_URS", "terra_contract_guarantee_owned_URS"})
        self.partner.flags.update({"terra_contract_active", "terra_contract_protected_SGN"})
        self.actor.relation("has_guaranteed", "URS")
        self.partner.attrs["has_defensive_war"] = True
        self.runtime.call("terra_contract_process_defense_effect", self.scope, TARGET="URS")
        self.assertNotIn("terra_contract_defense_call_URS", self.actor.flags)
        self.assertNotIn("terra_contract_active", self.actor.flags)
        # Relation effects are captured; the runner does not emulate native guarantees.
        removals = [node for key, node in self.actor.effects if key == "diplomatic_relation"]
        self.assertEqual(1, len(removals))
        self.assertEqual(("URS", "guarantee", "no"),
                         tuple(removals[0].scalar(key) for key in ("country", "relation", "active")))
        self.assertEqual(53, self.actor.variables["terra_state_reputation"])

    def test_closing_a_contract_preserves_a_guarantee_it_did_not_create(self):
        self.actor.relation("has_guaranteed", "URS")
        self.runtime.call("terra_contract_offer_defense_effect", self.scope)
        self.assertNotIn("terra_contract_pending", self.actor.flags)
        self.runtime.call("terra_contract_close_pair_effect", self.scope, TARGET="URS")
        self.assertIn("URS", self.actor.relations.get("has_guaranteed", set()))
        self.assertFalse(any(key == "diplomatic_relation" for key, _ in self.actor.effects))

    def test_annexation_subject_status_and_changed_faction_cancel_without_shipment(self):
        for country, attribute, value in (("URS", "exists", False), ("SGN", "is_subject", True), ("SGN", "is_in_faction", True)):
            with self.subTest(country=country, attribute=attribute):
                self.setUp()
                self.sign_aid()
                self.runtime.country(country).attrs[attribute] = value
                self.runtime.call("terra_contract_due_aid_effect", self.scope)
                self.assertEqual((1000, 200), self.stocks())
                self.assertNotIn("terra_contract_active", self.actor.flags)
                self.assertNotIn("terra_contract_active", self.partner.flags)

    def test_defense_is_honored_only_against_the_clients_actual_aggressor(self):
        self.actor.flags.update({"terra_contract_active", "terra_contract_defender_URS", "terra_contract_guarantee_owned_URS", "terra_contract_defense_term_URS"})
        self.partner.flags.update({"terra_contract_active", "terra_contract_protected_SGN"})
        self.actor.relation("has_guaranteed", "URS")
        self.partner.attrs["has_defensive_war"] = True
        self.actor.relation("has_war_with", "CLM")
        self.assertFalse(self.runtime.trigger("terra_contract_aiding_defense_of", self.scope, TARGET="URS"))
        self.runtime.call("terra_contract_process_defense_effect", self.scope, TARGET="URS")
        self.assertEqual(50, self.actor.variables["terra_state_reputation"])
        self.assertIn("terra_contract_defense_call_URS", self.actor.flags)
        self.partner.relation("has_defensive_war_with", "CLM")
        self.assertTrue(self.runtime.trigger("terra_contract_aiding_defense_of", self.scope, TARGET="URS"))
        self.runtime.call("terra_contract_process_defense_effect", self.scope, TARGET="URS")
        self.assertEqual(53, self.actor.variables["terra_state_reputation"])
        self.assertEqual(18, self.partner.variables["terra_dip_trust_SGN"])
        self.runtime.call("terra_contract_process_defense_effect", self.scope, TARGET="URS")
        self.assertEqual(53, self.actor.variables["terra_state_reputation"])
        self.actor.attrs["is_ai"] = False
        self.assertFalse(self.runtime.trigger("terra_contract_defense_obligation_to", self.scope, TARGET="URS"))

    def test_human_negotiation_timeouts_decline_without_signing_a_commitment(self):
        events = {node.scalar("id"): node for node in read(MOD / "events/terra_commitment_events.txt") if node.key == "country_event"}
        for event_id in ("terra_promises.2", "terra_promises.3", "terra_promises.4", "terra_promises.21", "terra_promises.22", "terra_promises.23"):
            with self.subTest(event=event_id):
                default = events[event_id].fields("option")[0]
                self.assertEqual(event_id + ".c", default.scalar("name"))
                self.assertFalse(any(node.key in {"terra_contract_sign_aid_effect", "terra_contract_sign_defense_effect", "send_equipment", "give_guarantee"} for node in walk(default.children)))
        self.runtime.call("terra_contract_offer_aid_effect", self.scope)
        decline = events["terra_promises.3"].fields("option")[0]
        self.runtime.execute(tuple(node for node in decline.children if node.key not in {"name", "trigger", "ai_chance"}), self.scope)
        self.assertEqual((1000, 200), self.stocks())
        self.assertNotIn("terra_contract_pending", self.actor.flags)
        self.assertNotIn("terra_contract_pending", self.partner.flags)
        self.assertNotIn("terra_contract_active", self.actor.flags)


class NewNativeStructureTests(unittest.TestCase):
    def test_strategic_system_never_mints_resources_or_forces_war_results(self):
        prohibited = {"add_equipment_to_stockpile", "add_manpower", "add_building_construction", "set_equipment_fraction",
                      "declare_war_on", "white_peace", "annex_country", "puppet", "create_faction"}
        prefixes = ("terra_strategic_state", "terra_security", "terra_commitments", "terra_war_director")
        found = []
        for folder in ("common/scripted_effects", "common/decisions", "events"):
            for path in sorted((MOD / folder).glob("*.txt")):
                if path.stem.startswith(prefixes):
                    found.append(path)
                    for node in walk(read(path)):
                        self.assertNotIn(node.key, prohibited, f"{path}:{node.line}")
        self.assertTrue(found)

    def test_new_ai_profiles_are_reversible(self):
        count = 0
        for name in ("terra_strategic_state.txt", "terra_security.txt", "terra_war_director.txt"):
            for profile in read(MOD / "common/ai_strategy" / name):
                count += 1
                self.assertEqual("yes", profile.scalar("abort_when_not_enabled"), profile.key)
                self.assertIsNotNone(profile.one("enable"), profile.key)
        self.assertGreater(count, 0)


if __name__ == "__main__":
    unittest.main()
