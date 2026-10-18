"""Verify the native-AI boundary, not HOI4 recruitment or combat behavior.

The installed game's AI scripts are deliberately not vendored or simulated.
These checks catch a blocked fallback, an old controller returning, or a
story exception affecting an ordinary country.
"""
import re
import unittest

from tools.validate_diplomacy import MOD, Runtime, read, walk


class NativeAIBaselineTests(unittest.TestCase):
    def test_both_descriptors_allow_installed_generic_ai_files(self):
        required = {
            'common/ai_strategy', 'common/ai_templates', 'common/ai_equipment',
            'common/ai_navy/goals', 'common/peace_conference/ai_peace',
        }
        descriptors = (MOD / 'descriptor.mod', MOD.parent / 'Dawn_of_Terra.mod')
        for path in descriptors:
            replacements = {n.value for n in read(path) if n.key == 'replace_path'}
            with self.subTest(path=path.name):
                for target in required:
                    self.assertFalse(any(target == root or target.startswith(root + '/')
                                         for root in replacements), target)
                # Earth-specific focus plans and theaters do not fit Terra's map.
                self.assertIn('common/ai_strategy_plans', replacements)
                self.assertIn('common/ai_faction_theaters', replacements)

    def test_only_the_two_documented_story_strategy_exceptions_remain(self):
        profiles = {n.key: n for p in (MOD / 'common/ai_strategy').glob('*.txt')
                    for n in read(p)}
        self.assertEqual({'terra_gaul_wait_for_1029', 'terra_tnj_no_army'}, set(profiles))
        for profile in profiles.values():
            self.assertEqual('yes', profile.scalar('abort_when_not_enabled'))

    def test_no_custom_templates_designs_naval_goals_or_allied_theaters_load(self):
        for directory in ('ai_templates', 'ai_equipment', 'ai_navy/goals', 'ai_faction_theaters'):
            for path in (MOD / 'common' / directory).glob('*.txt'):
                with self.subTest(path=path):
                    self.assertEqual((), read(path))

    def test_no_lua_ai_define_overrides_remain(self):
        for path in (MOD / 'common/defines').glob('*.lua'):
            source = re.sub(r'--[^\n]*', '', path.read_text(encoding='utf-8-sig'))
            self.assertNotRegex(source, r'NDefines\s*\.\s*NAI\s*\.')

    def test_custom_areas_only_adapt_the_global_continent_to_terra(self):
        areas = read(MOD / 'common/ai_areas/terra_areas.txt')[0]
        self.assertEqual(['globally'], [n.key for n in areas.children])
        self.assertEqual(['Terra'], [n.key for n in areas.one('globally').one('continents').children])

    def test_director_entry_hooks_are_removed_and_story_hooks_remain(self):
        for filename in ('terra_ai_capacity.txt', 'terra_wartime_routes.txt'):
            self.assertEqual((), read(MOD / 'common/on_actions' / filename))
        hooks = read(MOD / 'common/on_actions/terra_diplomacy.txt')[0]
        self.assertEqual({'on_daily', 'on_weekly'}, {n.key for n in hooks.children})
        self.assertEqual({'terra_story_gaul_launch_1029_effect', 'terra_story_gaul_advance_focus_effect'},
                         {n.key for hook in hooks.children for n in hook.one('effect').children})

    def test_no_retired_controller_definitions_or_references_remain(self):
        retired = re.compile(r'^terra_(ai_|dip_|state_|war_|security_|coalition_|contract_|commitment_|subject_)')
        for directory in ('common', 'events', 'history'):
            for path in (MOD / directory).rglob('*.txt'):
                # Country colors use typed rgb/hsv blocks outside this parser's scope.
                if path.parent.name == 'countries' and path.parent.parent.name == 'common':
                    continue
                for node in walk(read(path)):
                    if node.key == 'terra_tnj_no_army':
                        continue
                    self.assertIsNone(retired.match(node.key), f'{path}:{node.line}: {node.key}')

    def test_standard_recruitment_is_not_replaced_by_a_new_scripted_workaround(self):
        prohibited = {'add_ai_strategy', 'remove_ai_strategy', 'force_build_armies',
                      'build_army', 'ai_wanted_divisions_factor', 'role_ratio'}
        exceptions = {'common/ai_strategy/terra_subject_recruitment.txt'}
        for directory in ('common/ai_strategy', 'common/scripted_effects', 'common/on_actions', 'events'):
            for path in (MOD / directory).glob('*.txt'):
                if path.relative_to(MOD).as_posix() in exceptions:
                    continue
                for node in walk(read(path)):
                    self.assertNotIn(node.key, prohibited, f'{path}:{node.line}')
                    if node.key == 'ai_strategy':
                        self.assertNotIn(node.scalar('type'), prohibited, f'{path}:{node.line}')

    def test_story_strategy_exceptions_never_apply_to_normal_countries(self):
        runtime = Runtime()
        profiles = [n for p in (MOD / 'common/ai_strategy').glob('*.txt') for n in read(p)]
        # Real registry, including dynamic tags and the newest western satrapies.
        for tag in runtime.countries:
            if tag in {'LGL', 'TNJ'}:
                continue
            scope = runtime.scope(tag)
            for subject in (False, True):
                runtime.country(tag).attrs['is_subject'] = subject
                for profile in profiles:
                    self.assertFalse(runtime.check(profile.one('allowed').children, scope), (tag, subject, profile.key))

    def test_story_hooks_leave_gaul_and_victoria_recruitment_inputs_untouched(self):
        for tag in ('LGL', 'VCT'):
            for subject in (False, True):
                runtime = Runtime()
                scope = runtime.scope(tag)
                actor = runtime.country(tag)
                actor.attrs['is_subject'] = subject
                before = (dict(actor.stockpiles), actor.attrs['has_manpower'], actor.attrs['num_divisions'])
                hooks = read(MOD / 'common/on_actions/terra_diplomacy.txt')[0]
                for hook in hooks.children:
                    runtime.execute(hook.one('effect').children, scope)
                self.assertEqual(before, (actor.stockpiles, actor.attrs['has_manpower'], actor.attrs['num_divisions']))
                self.assertFalse(any(key in {'create_unit', 'load_oob', 'add_manpower', 'delete_unit',
                                              'country_lock_all_division_template', 'add_equipment_to_stockpile'}
                                     for key, _ in actor.effects))

    def test_removed_decision_menus_stay_empty(self):
        for directory in ('common/decisions', 'common/decisions/categories'):
            for filename in ('terra_diplomatic_desk.txt', 'terra_commitments.txt', 'terra_strategic_report.txt'):
                self.assertEqual((), read(MOD / directory / filename))


if __name__ == '__main__':
    unittest.main()
