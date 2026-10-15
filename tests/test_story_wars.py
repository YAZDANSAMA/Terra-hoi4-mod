"""Authored focus-war routing; native legality and scheduling remain fixtures."""
import unittest

from tools.validate_diplomacy import EventDelivery, MOD, Runtime, read


class GaulStoryWarTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.scope = self.runtime.scope("LGL")
        self.actor = self.runtime.country("LGL")
        self.runtime.scope("LTH")
        self.target = self.runtime.country("LTH")
        self.actor.completed_focuses.add("LGL_wo4e_start")
        self.actor.flags.add("LTH_envoy_refuse")
        # Explicit native facts, not a simulation of focus completion or legality.
        self.actor.relation("has_wargoal_against", "LTH")
        self.actor.relation("can_declare_war_on", "LTH")
        tree = read(MOD / "common/national_focus/LGL_national_focus.txt")[0]
        self.focus = next(n for n in tree.fields("focus") if n.scalar("id") == "LGL_wo4e_start")

    def start(self):
        self.runtime.call("terra_story_gaul_start_war_effect", self.scope)

    def declarations(self):
        return [node for key, node in self.actor.effects if key == "declare_war_on"]

    def test_focus_retains_wargoal_and_only_schedules_ai_continuation(self):
        reward = self.focus.one("completion_reward")
        self.assertEqual("LTH", reward.one("create_wargoal").scalar("target"))
        self.runtime.execute(reward.children, self.scope)
        self.assertEqual([EventDelivery("LGL", "LGL", "terra_story_wars.1", "1")], self.runtime.deliveries)
        self.assertFalse(self.declarations())
        self.actor.attrs["is_ai"] = False
        self.runtime.deliveries.clear()
        self.runtime.execute(reward.children, self.scope)
        self.assertFalse(self.runtime.deliveries)

    def test_hidden_event_fulfills_the_completed_war_branch_once(self):
        event = next(n for n in read(MOD / "events/terra_story_wars.txt") if n.key == "country_event")
        self.assertEqual("yes", event.scalar("hidden"))
        self.assertEqual("yes", event.scalar("is_triggered_only"))
        self.runtime.execute(event.one("immediate").children, self.scope)
        self.assertEqual("LTH", self.declarations()[0].scalar("target"))
        self.assertEqual("annex_everything", self.declarations()[0].scalar("type"))
        self.assertIn("LGL", self.target.relations["has_defensive_war_with"])
        self.assertIn("terra_story_gaul_war_started", self.actor.flags)
        self.start()
        self.assertEqual(1, len(self.declarations()))
        # Even a later peace and another wargoal must not replay this story war.
        self.actor.relation("has_war_with", "LTH", False)
        self.actor.relation("has_wargoal_against", "LTH")
        self.start()
        self.assertEqual(1, len(self.declarations()))

    def test_old_save_with_completed_focus_is_repaired_by_actual_weekly_hook(self):
        hook = read(MOD / "common/on_actions/terra_diplomacy.txt")[0].one("on_weekly").one("effect")
        # No scheduled event or new focus-only flag exists in this old-save fixture.
        self.runtime.execute(hook.children, self.scope)
        self.assertEqual(1, len(self.declarations()))

    def test_story_intent_is_not_blocked_by_sandbox_scores_or_low_strength(self):
        self.actor.attrs.update({"has_war": True, "has_manpower": 5000, "army_strength": 20})
        self.actor.stockpiles["infantry_equipment"] = 100
        self.actor.variables.update({"terra_state_war_fatigue": 90, "terra_dip_grievance_LTH": 0})
        self.actor.flags.add("terra_state_goal_recovery")
        self.assertFalse(self.runtime.trigger("terra_dip_can_seek_war_against", self.scope, TARGET="LTH"))
        self.start()
        self.assertEqual(1, len(self.declarations()))

    def test_wargoal_alone_or_unfinished_focus_cannot_authorize_story_war(self):
        self.actor.completed_focuses.clear()
        self.start()
        self.assertFalse(self.declarations())
        self.actor.completed_focuses.add("LGL_wo4e_start")
        self.actor.flags.clear()
        self.start()
        self.assertFalse(self.declarations())

    def test_legality_and_diplomatic_safeguards_are_checked_at_execution(self):
        for kind in ("no_goal", "illegal", "nap", "same_faction", "already_at_war", "actor_subject",
                     "target_subject", "actor_capitulated", "target_capitulated", "target_missing"):
            with self.subTest(kind=kind):
                self.setUp()
                if kind == "no_goal": self.actor.relation("has_wargoal_against", "LTH", False)
                elif kind == "illegal": self.actor.relation("can_declare_war_on", "LTH", False)
                elif kind == "nap": self.actor.relation("has_non_aggression_pact_with", "LTH")
                elif kind == "same_faction": self.actor.relation("is_in_faction_with", "LTH")
                elif kind == "already_at_war": self.actor.relation("has_war_with", "LTH")
                elif kind == "actor_subject": self.actor.attrs["is_subject"] = True
                elif kind == "target_subject": self.target.attrs["is_subject"] = True
                elif kind == "actor_capitulated": self.actor.attrs["has_capitulated"] = True
                elif kind == "target_capitulated": self.target.attrs["has_capitulated"] = True
                else: self.target.attrs["exists"] = False
                self.start()
                self.assertFalse(self.declarations())

    def test_temporary_legal_blocker_can_expire_without_losing_story_intent(self):
        self.actor.relation("can_declare_war_on", "LTH", False)
        self.start()
        self.assertNotIn("terra_story_gaul_war_started", self.actor.flags)
        self.actor.relation("can_declare_war_on", "LTH")
        self.start()
        self.assertEqual(1, len(self.declarations()))

    def test_humans_and_other_countries_never_receive_automatic_story_wars(self):
        self.actor.attrs["is_ai"] = False
        self.start()
        self.assertFalse(self.declarations())
        for tag in self.runtime.countries:
            if tag == "LGL":
                continue
            scope = self.runtime.scope(tag)
            country = self.runtime.country(tag)
            country.completed_focuses.add("LGL_wo4e_start")
            country.flags.add("LTH_envoy_refuse")
            country.relation("has_wargoal_against", "LTH")
            country.relation("can_declare_war_on", "LTH")
            self.runtime.call("terra_story_gaul_start_war_effect", scope)
            self.assertFalse(any(k == "declare_war_on" for k, _ in country.effects), tag)
        self.actor.attrs.update({"is_ai": True, "original_tag": "D01"})
        self.start()
        self.assertFalse(self.declarations())

    def test_submission_and_backdown_block_both_new_and_pending_execution(self):
        for flag in ("LTH_envoy_submit", "terra_story_gaul_backed_down"):
            with self.subTest(flag=flag):
                self.actor.flags.add(flag)
                self.start()
                self.assertFalse(self.declarations())
                self.actor.flags.discard(flag)
        self.actor.completed_focuses.add("LGL_wo4e_skip")
        self.start()
        self.assertFalse(self.declarations())

    def test_actual_backdown_option_disables_focus_and_future_story_declarations(self):
        event = next(n for n in read(MOD / "events/LGL_events.txt") if n.key == "country_event" and n.scalar("id") == "gaul.102")
        option = next(n for n in event.fields("option") if n.scalar("name") == "gaul.102.b")
        self.runtime.execute(tuple(n for n in option.children if n.key not in {"name", "ai_chance"}), self.scope)
        self.assertIn("terra_story_gaul_backed_down", self.actor.flags)
        self.assertFalse(self.runtime.check(self.focus.one("available").children, self.scope))
        self.start()
        self.assertFalse(self.declarations())


if __name__ == "__main__":
    unittest.main()
