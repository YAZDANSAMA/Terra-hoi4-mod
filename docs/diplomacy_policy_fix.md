# Pact spam and wartime coalition correction

Updated 2026-10-15, based on the report that countries flooded each other with non-aggression pacts at the start and did not create factions against a shared enemy.

The later [defensive coalition bootstrap correction](defensive_coalition_fix.md) addresses the reported Sargon-versus-Bolivar-and-Columbia case. It explicitly declares ideology join permissions, permits mutual-defense cooperation despite ideological dislike, and adds a next-day war hook. Its result checks and the current 98-test suite supersede the timing and fixture assumptions described below.

## Causes and resulting behavior

The old restraint strategy required utility above 9, low grievances and either adjacency, exhaustion or a cautious personality. Same-government utility alone was +10. A cautious country could therefore encourage and accept pacts with neutral countries before earning trust. The +35 proposal and acceptance weights amplified that behavior.

Every one of the 79 target profiles now uses `terra_dip_can_offer_restraint`. A native AI pact needs earned trust above 39, utility above 39, grievances below 20, positive opinions in both directions, an adjacent independent partner and an ongoing war or substantial war fatigue. It cannot target its enemy, a shared-war ally, a faction partner, a core-territory rival, a country with a bilateral war goal, or an observed threat/warning target. Eligible preferences are +10. Outside these conditions, reversible −1000 proposal and acceptance strategies discourage the engine's generic offers. Caution and ideology alone no longer qualify.

Authored player restraint negotiations remain explicit choices. Existing pacts are neither deleted nor broken by the correction. To check the original startup problem, use a fresh campaign: loading an older save retains the pacts that were already signed.

Previously, common-threat behavior only raised alliance and invitation preferences. Most countries also lacked permission to create a faction. `terra_coalition_weekly_effect` now forms a real faction when two eligible independent AI countries are already fighting the **same live enemy**. It grants creation permission only to the selected AI leader, chooses one of three existing localized faction names for that leader's ideology, creates the faction and adds the qualifying AI partner. Countries sharing only an ideology or fighting different enemies cannot qualify. Multiple common enemies are supported.

The generated faction can enroll further independent AI countries sharing an actual enemy with its leader. It never transfers a member out of another faction, replaces an existing story faction, enrolls a player, recruits a subject, ignores a country join ban or starts a war. A member leaving a generated coalition receives a one-year re-entry cooldown. Existing Sargon membership and Siesta, Seaborn and Ta-Netjer exclusions remain intact. The No Compromise, No Surrender path uses a neutral faction template with a defensive charter and no resource/stat rewards; the non-DLC path follows the mod's existing legacy faction-creation pattern.

## Validation and limits

`python3 tools/validate_diplomacy.py` passed **90 tests**, including all 77 prior scenarios. New actual-AST scenarios cover the neutral startup matrix across all 81 registered tags after score/personality refresh, the positive wartime pact case, claims/war goals/warnings, existing pacts, common versus different enemies, real roster formation and extension, idempotence, players/subjects/foreign factions/join bans, defeated enemies, and all three faction-name choices with the template DLC path. Roster state and random branches are controlled fixtures, not HOI4 engine or randomness simulation.

The unchanged native CWTools schema found **zero errors across all nine added or modified native files and instantiated macro bodies**. The pass used 46 parameterized definitions, 5,103 materialized instances and 30,694 rewritten calls in a disposable mirror, with stable source hashes and the five documented equipment enum fixtures described in [native_validation_strategic.md](native_validation_strategic.md). Its 30 warnings include 28 legacy `create_faction` deprecation warnings from the explicitly guarded non-DLC fallback and two unnecessary OR wrappers. The whole-mod report still has 29,968 diagnostics; it is not a full-mod validation pass. Environment evidence is `/tmp/terra-pact-coalition-fix-1-{manifest,report,changed,summary}.json`.

Read-only source/asset validation also passed: 749 script structures, 4 Lua files, 54 localization files with 3,418 entries, 999 images, five audio tracks, country targets and map/state references. HOI4 is not installed here. In-game checks remain necessary for native AI evaluation, faction naming, creation permission, UI membership, DLC combinations and campaign balance.

## In-game reproduction checks

1. Start a fresh campaign and advance several weekly pulses. Neutral cautious countries should not send a global wave of pacts.
2. Build genuine confidence with an adjacent country while facing a separate war. A limited, useful pact can still be proposed; a bilateral claim or war goal should prevent that preference.
3. Put two independent AI countries outside factions at war with the same country. After a weekly pulse, check their faction list and map: they should share a named faction if opinions, grievances and country permissions permit it.
4. Repeat with different enemies, a player, a subject and a member of an existing faction. Those cases should not be enrolled automatically.
5. Give a third independent AI country a war against the generated faction leader's enemy. It can join the generated faction; wars and story blocs elsewhere must remain intact.
6. Repeat with and without the faction-template DLC and after save/reload. Inspect `error.log`, native roster/names and whether a voluntarily departing member remains out during its cooldown.
