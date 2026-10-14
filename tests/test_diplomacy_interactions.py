"""Evaluate actual event/decision branches with explicit ROOT/FROM fixtures.

The fixture records native country_event handoffs and runs requested immediate
blocks. It does not simulate HOI4 event timing or prove engine source scopes.
"""
import unittest

from tools.validate_diplomacy import EventDelivery, MOD, Runtime, Scope, read, walk


class NegotiationTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.runtime.country("SGN").attrs["is_ai"] = False
        for tag in ("SGN", "URS"):
            self.runtime.call("terra_dip_initialize_effect", self.runtime.scope(tag))
        self.actor = self.runtime.country("SGN")
        self.recipient = self.runtime.country("URS")
        self.scope = self.runtime.scope("URS", "SGN")
        self.events = {node.scalar("id"): node for node in read(MOD / "events/terra_diplomacy_events.txt") if node.key == "country_event"}

    def options(self, event_id):
        return self.events[event_id].fields("option")

    def option(self, event_id, suffix):
        return next(option for option in self.options(event_id) if option.scalar("name") == event_id + "." + suffix)

    def available(self, option):
        trigger = option.one("trigger")
        return trigger is None or self.runtime.check(trigger.children, self.scope)

    def option_effects(self, option):
        return tuple(node for node in option.children if node.key not in {"name", "trigger", "ai_chance", "default", "highlighted"})

    def war(self):
        self.actor.relation("has_war_with", "URS")
        self.recipient.relation("has_war_with", "SGN")

    def deliver(self, delivery):
        event = self.events[delivery.event_id]
        immediate = event.one("immediate")
        if immediate is not None:
            self.runtime.execute(immediate.children, Scope(delivery.recipient, delivery.recipient, delivery.sender))

    def test_normal_options_and_withdrawal_are_mutually_exclusive(self):
        for event_id in ("terra_talks.2", "terra_talks.11", "terra_talks.21", "terra_talks.23", "terra_talks.31"):
            with self.subTest(event=event_id):
                self.setUp()
                options = self.options(event_id)
                normal = [option for option in options if not option.scalar("name").endswith(".withdraw")]
                withdrawal = [option for option in options if option.scalar("name").endswith(".withdraw")]
                self.assertEqual(1, len(withdrawal))
                self.assertTrue(normal)
                self.assertTrue(all(self.available(option) for option in normal))
                self.assertFalse(self.available(withdrawal[0]))
                self.war()
                self.assertFalse(any(self.available(option) for option in normal))
                self.assertTrue(self.available(withdrawal[0]))

    def test_missing_or_subject_country_leaves_only_withdrawal(self):
        for event_id in ("terra_talks.2", "terra_talks.11", "terra_talks.21", "terra_talks.23", "terra_talks.31"):
            for tag in ("SGN", "URS"):
                for attribute, value in (("exists", False), ("is_subject", True), ("has_capitulated", True)):
                    with self.subTest(event=event_id, tag=tag, attribute=attribute):
                        self.setUp()
                        self.runtime.country(tag).attrs[attribute] = value
                        enabled = [option.scalar("name") for option in self.options(event_id) if self.available(option)]
                        self.assertEqual([event_id + ".withdraw"], enabled)

    def test_delayed_request_relays_preserve_the_two_expected_countries(self):
        for first, relay, visible in (("1", "101", "2"), ("10", "110", "11"), ("20", "120", "21"), ("30", "130", "31")):
            with self.subTest(first=first):
                self.setUp()
                self.deliver(EventDelivery("URS", "SGN", "terra_talks." + first, "3"))
                self.assertEqual(1, len(self.runtime.deliveries))
                self.assertEqual(("SGN", "URS", "terra_talks." + relay), (self.runtime.deliveries[0].recipient, self.runtime.deliveries[0].sender, self.runtime.deliveries[0].event_id))
                middle = self.runtime.deliveries.pop()
                self.deliver(middle)
                self.assertEqual([EventDelivery("URS", "SGN", "terra_talks." + visible, "0")], self.runtime.deliveries)

    def test_request_and_relay_both_recheck_war_then_refund_sender(self):
        for first, refund, cost in (("1", "60", 15), ("10", "61", 35), ("20", "62", 40), ("30", "63", 25)):
            for stage in ("request", "relay"):
                with self.subTest(first=first, stage=stage):
                    self.setUp()
                    delivery = EventDelivery("URS", "SGN", "terra_talks." + first, "3")
                    if stage == "relay":
                        self.deliver(delivery)
                        delivery = self.runtime.deliveries.pop()
                    self.war()
                    self.deliver(delivery)
                    self.assertEqual(1, len(self.runtime.deliveries))
                    cancelled = self.runtime.deliveries.pop()
                    self.assertEqual("SGN", cancelled.recipient)
                    self.assertEqual("terra_talks." + refund, cancelled.event_id)
                    old_power = self.actor.attrs["political_power"]
                    self.deliver(cancelled)
                    self.assertEqual(old_power + cost, self.actor.attrs["political_power"])

    def test_click_time_recheck_cannot_sign_pact_or_change_memory_after_war(self):
        for event_id in ("terra_talks.2", "terra_talks.11", "terra_talks.21", "terra_talks.23", "terra_talks.31"):
            with self.subTest(event=event_id):
                self.setUp()
                accepting = self.option(event_id, "a")
                self.assertTrue(self.available(accepting))
                old_actor = dict(self.actor.variables)
                old_recipient = dict(self.recipient.variables)
                self.war()
                self.runtime.execute(self.option_effects(accepting), self.scope)
                self.assertEqual(old_actor, self.actor.variables)
                self.assertEqual(old_recipient, self.recipient.variables)
                self.assertFalse(any(key == "diplomatic_relation" for key, node in self.recipient.effects))

    def test_dialogue_updates_actual_bilateral_memories(self):
        self.runtime.execute(self.option_effects(self.option("terra_talks.2", "a")), self.scope)
        self.assertEqual(8, self.actor.variables["terra_dip_trust_URS"])
        self.assertEqual(8, self.recipient.variables["terra_dip_trust_SGN"])
        self.assertEqual(0, self.actor.variables["terra_dip_grievance_URS"])
        self.assertEqual(0, self.recipient.variables["terra_dip_grievance_SGN"])
        self.assertEqual("SGN", self.runtime.deliveries[-1].recipient)

    def test_civil_war_can_seek_external_talks_but_not_its_opponent(self):
        self.recipient.attrs.update({"has_civil_war": True, "has_war": True})
        self.assertTrue(self.runtime.trigger("terra_dip_talks_available_from", self.scope))
        self.war()
        self.assertFalse(self.runtime.trigger("terra_dip_talks_available_from", self.scope))

    def test_every_scheduled_dialogue_event_exists(self):
        for path in (MOD / "events/terra_diplomacy_events.txt", MOD / "common/scripted_effects/terra_diplomatic_outreach.txt", MOD / "common/decisions/terra_diplomatic_desk.txt"):
            for node in walk(read(path)):
                if node.key == "country_event" and node.scalar("id", "").startswith("terra_talks."):
                    self.assertIn(node.scalar("id"), self.events, f"{path}:{node.line}")

    def test_unanswered_human_proposal_defaults_to_declining(self):
        for event_id in ("terra_talks.2", "terra_talks.11", "terra_talks.21", "terra_talks.23", "terra_talks.31"):
            with self.subTest(event=event_id):
                suffix = ".b" if event_id == "terra_talks.23" else ".c"
                self.assertEqual(event_id + suffix, self.options(event_id)[0].scalar("name"))
                self.assertEqual("30", self.events[event_id].scalar("timeout_days"))
                # Simulate only the default option branch, not engine timing.
                self.runtime.execute(self.option_effects(self.options(event_id)[0]), self.scope)
                self.assertFalse(any(key == "diplomatic_relation" for key, node in self.recipient.effects))


if __name__ == "__main__":
    unittest.main()
