> Historical implementation notes. The custom AI and its test counts below were retired.
> See [the current native AI baseline](native_ai_baseline.md) for active behavior and validation.

# Defensive coalition bootstrap correction

Updated 2026-10-15 after the report that player-controlled Sargon could fight Bolivar and Columbia without either AI forming a common faction. The reported game uses the non-DLC faction-creation path. The earlier non-aggression correction remains unchanged.

## Corrections

The coalition actor required `has_rule = can_join_factions`, but none of the nine custom ideology rule blocks explicitly declared that permission. The regression fixture supplied a positive country default and consequently could not expose a missing configuration. All nine ideology groups now declare `can_join_factions = yes`; the test interpreter reads their actual rules instead of supplying this permission itself. Explicit country bans still override ideology defaults. Creation permission remains granted only to an eligible AI founder at formation; this does not grant every country permission to create factions at startup.

The previous mutual-opinion floor could also reject two countries defending against the same attacker because their governments dislike each other. It remains applicable to ordinary common-war cooperation, but is bypassed when **both prospective partners have a defensive war against the same actual enemy**. Bilateral war goals, severe recorded grievances, subjects, player governments, defeated countries, join bans, existing story/foreign factions and departure cooldowns retain their guards.

`on_war_relation_added` schedules a hidden coalition check for participating AI governments after one day, rather than relying solely on the seven-day pulse. Each recipient event resets ROOT to its own government before evaluating country pairs. A pending flag deduplicates rapid war relations; the existing weekly pulse still covers loaded wars and missed event checks. The scheduling policy is the same for the non-DLC legacy path and the faction-template DLC path.

Creation and enrollment results are now checked before flags or trust credit are granted. A failed operation is logged and its retry is throttled for seven days. Successful membership changes are credited only after `is_in_faction_with` confirms the actual relationship.

## Verification

`python3 tools/validate_diplomacy.py` passed **98 tests**, retaining all 90 previous scenarios. New tests load Bolivar's actual starting `junta` government and Columbia's `classical_liberalism` government from their history files. The scenario uses human-controlled Sargon as their common aggressor and negative Bolivar–Columbia opinions. It forms a Bolivar–Columbia faction in both controlled DLC branches, without changing Sargon's existing faction. Additional scenarios reproduce missing ideology permission, preserve an explicit country join ban, reject the dislike exception for different defensive enemies, verify war-hook delivery and ROOT reset, and exercise failed native creation/enrollment without phantom membership or trust.

These are actual script AST tests with controlled country facts, event delivery and faction-result fixtures. They do not execute the game, its scheduler or DLC internals. HOI4 is unavailable in the cloud environment; the player's runtime observation remains essential.

The unchanged CWTools schema found **zero errors across all five added or modified native files and instantiated macro bodies**. The 28 warnings concern the legacy faction-creation fallback, also used by the existing Sargon setup; the non-DLC regression scenario exercises that branch. The full unfiltered mod report still contains 29,968 diagnostics, so this is not a full-mod native pass. The source remained stable during validation. Environment evidence is `/tmp/terra-defender-coalition-fix-2-{manifest,report,changed,summary}.json`; the disposable mirror used 47 parameterized definitions, 5,182 concrete instances, 30,773 rewritten calls and the five documented enum fixtures.

Source/asset checks also passed with zero failures: 750 script structures, four Lua files, 54 localization files, 3,418 localization entries, 999 images, five audio tracks and the existing country/map/state references.

## In-game check

Install the updated mod and restart HOI4 to load the revised ideology rules and hook. As Sargon, declare war on independent AI Bolivar and Columbia while both are still active. Advance beyond the day following the second declaration; check their faction lists and the map. Repeat without and with the faction-template DLC where available. Existing saves also retain the weekly fallback, but new configuration must first be loaded by restarting the game.

Inspect `Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log` for lines beginning `Terra coalition:`. They record the war-triggered check, successful creation/enrollment, or the operation that failed. No faction check can recruit a player government or move a member out of another existing faction. No war is started, and no existing pact is removed by this update.
