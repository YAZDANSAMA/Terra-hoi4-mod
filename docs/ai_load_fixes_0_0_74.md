# Terra AI loading and Sargon industry — v0.0.74

This integrates the tested `Dawn_of_Terra_0.0.74_AI_Schema_Fix.zip` with upstream
`b4b5e780bee666360687960569f8d58a92116de7`. The 1,924 packaged game files
are preserved byte for byte. Relative to that upstream commit, the package
changes 37 state histories, 17 AI files and both main-mod descriptors.

## AI corrections

The first player log rejected U+FEFF as a database entry in 17 generated AI
files, including recruitment, production and division templates. The source
parser normalized away that character, so earlier AST checks missed it.
Remove only the leading UTF-8 BOM from those files. Localisation encoding is
unchanged. Regression coverage inspects raw bytes before parser normalization.

Both descriptors explicitly replace `common/ai_navy/goals`,
`common/ai_navy/fleet` and `common/ai_navy/taskforce`. A parent-only replacement
had allowed installed Earth-specific naval files to load in the player's setup.

After the encoding repair, a second log exposed 20 native field/type errors:

- Remove the rejected `template_xp_reserve` strategy and unsupported
  `strike_force_objective` goal. Existing XP priorities, the other ten naval
  objectives and strike fleet/taskforce definitions remain.
- Use `armor`, `screen_ship` and `capital_ship` equipment categories for the
  rejected production ratios. Combine the former screen weights 45 and 15 into
  60; preserve other values and division-role ratios.
- Match twelve rejected legacy design targets to the concrete equipment IDs
  unlocked by their existing technology requirements. Naval bomber IDs use
  `nav_bomber_equipment_1` and `cv_nav_bomber_equipment_1`.
- Replace the invalid armor module token with `ship_armor_bb_1`, unlocked by
  the existing heavy-hull technology requirement.

Recruitment targets and activation triggers are unchanged. No free units,
equipment, manpower, technology or new AI define overrides are introduced.
TNJ's scoped army lock and the existing story exceptions remain. The absent
upstream generator is not reconstructed; these are direct repairs of its output.

## Sargon and satrapy industry

The earlier reviewed v0.0.71 industry setup is included: 37 states, 79 million
population, 425 base shared slots, 109 civilian factories and 68 military
factories. Categories, extra shared slots and those two factory types are the
only state-history fields changed. Ownership, cores, population, cities,
resources, initial armies, map assets and the separate music addon are preserved.
These are base slot counts, before in-game national or technology modifiers.

| Country | Shared slots | Civilian | Military |
| --- | ---: | ---: | ---: |
| SGN | 105 | 30 | 24 |
| MSN | 35 | 12 | 8 |
| VVA | 70 | 12 | 10 |
| PSE | 82 | 16 | 9 |
| TNJ | 54 | 14 | 3 |
| GRM | 19 | 6 | 3 |
| HTR | 28 | 10 | 6 |
| PLM | 32 | 9 | 5 |

## Observed game results and limits

The player tested HOI4 1.19.3. The subsequent `error(2).log` has none of the
20 native AI diagnostics, BOM diagnostics or earlier installed naval-goal
diagnostics. `error(3).log` reaches 1031.8.2 without those errors returning.
Existing vanilla-derived and GUI diagnostics remain; this is not a claim that
the entire mod has a clean error log.

The supplied save `SGN_1031_10_01_02.hoi4` was decoded locally, without changing
or externally uploading it. It contains genuine open native training queues:
CLM infantry at 53.28% with 6,000 manpower and 600 equipment; IBR garrison at
48.884% with 4,000 manpower and 400 equipment.

| Country | Initial OOB divisions | Fielded in the 1031 save |
| --- | ---: | ---: |
| SGN | 27 | 32 |
| MSN | 15 | 16 |
| VVA | 21 | 23 |
| PSE | 22 | 25 |
| GRM | 15 | 18 |
| HTR | 13 | 21 |
| PLM | 11 | 21 |
| TNJ | 0 | 0 |
| VCT | 22 | 30 |
| URS | 28 | 43 |

The save's current player is SGN; the player confirmed switching tags for
inspection. Only TNJ has a country-wide template lock. None of the satrapies
has a live training queue at this timestamp, although additional fielded units
are present. LGL has scripted focus spawns, so its entire increase must not be
attributed to recruitment. The saved difficulty is `very_easy`; optimal training
rates, force composition, combat behavior and balance are not established.

Run source checks with `python3 -B tools/validate_diplomacy.py`. They check
script structure and boundaries; the observed game queues and units above,
not a passing test count, are the evidence that native recruitment is active.
No save or private log is committed to the repository.
