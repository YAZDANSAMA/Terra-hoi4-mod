# Strategic AI validation evidence

Validated on 2026-10-14. HOI4 and Steam are not installed in the cloud environment, so these results do not establish in-game behavior, campaign balance, save compatibility or CPU performance.

## Script regression scenarios

`python3 tools/validate_diplomacy.py` executes **77 tests**, including the 42 original diplomacy tests. They exercise actual mod script ASTs with explicit country facts and scopes. Scenarios cover state migration, ruler changes, bounded fatigue/reputation, capitulation memory, recovery hysteresis, warnings, intelligence margins, shared threats, subject duties, legacy remote-force limits, report scopes and fractional pressure bands.

Contract tests cover both aid quantities, conserved donor-to-recipient transfers, idempotent delivery, insufficient inventory, grace periods, late replenishment, pair isolation, cancellation, the client's actual defensive aggressor, term expiry and preservation of guarantees the contract did not create. Human proposal and confirmation defaults decline. The runner does not emulate HOI4's scheduler, flag expiry, equipment variants, guarantees or military AI; some native effects are captured for assertion rather than simulated.

## Source and asset checks

The read-only environment validator passed with zero failures: 743 structural script files, 4 Lua files, 53 localization files containing 3,391 entries, 999 decoded images and 5 decoded audio tracks. It also verified country targets, map references, 10,735 province definitions, 255 state files and 141 strategic-region files. These are source/asset checks, not a gameplay test.

## Native CWTools schema checks

Tools used:

- CWTools source: `b377453dee803f9258be92cfc49896d09039702d`.
- HOI4 schema: `297dd69c42aabe10078a8b7ab7f2d07ee631d4ef`.
- Official .NET SDK 9.0.319, previously verified against Microsoft's SHA-512 checksum.

The native validator cannot interpret block-valued parameterized scripted calls directly. A disposable mirror materialized exact named substitutions into 4,600 ordinary scripted helpers, covering 41 parameterized definitions and 23,556 call sites. Helpers preserve country scopes; no additional scope wrapper is inserted. Deduplication avoids combinatorial inlining exceeding CWTools' 8 MiB file limit. The tracked mod files were unchanged, and a SHA-256 manifest confirmed that the source remained stable during validation.

The mirror supplied five absent vanilla equipment enum members only: `infantry_equipment`, `support_equipment`, `artillery_equipment`, `motorized_equipment` and `train_equipment`. Every member was verified against the schema's game-generated `<Equipment>_design_cost_factor` documentation. The schema was not weakened, diagnostics were not suppressed, and no fabricated base-game equipment catalog was supplied.

The integrated pass covered all **30 added or modified native mod files**, including materialized helper bodies. It found **zero errors in the added files and new logic**. There were 23 warnings, primarily absent vanilla event/category sprites and redundant OR blocks. Four errors remained on unchanged lines of the modified legacy `common/ai_strategy/terra_ai_warfare.txt`:

| Original line | Unresolved reference | Diagnosis |
| --- | --- | --- |
| 19 | `has_terrain = mountain` | The vanilla terrain catalog is absent. Native documentation explicitly demonstrates this trigger/value. |
| 26 | `air_base > 0` | The vanilla building catalog is absent. The schema permits building-level checks in country and state scopes; game-generated documentation lists `air_base`. |
| 26 | `transport_plane_equipment` (two diagnostics) | The five-entry fixture omits this additional vanilla equipment enum member. Game-generated equipment documentation lists it. |

Each affected source line was compared with `origin/main` and is identical. These diagnostics are disclosed rather than removed or treated as a passed complete-file check. The unfiltered whole-mod report contains 29,939 diagnostics, including pre-existing content and unresolved vanilla references, so **full-mod native validation did not pass**.

Environment-local evidence: `/tmp/terra-strategic-final-2-{manifest,report,changed,summary}.json`, with validation helper `/workspace/terra-tools/native_strategic_validation.py`. These files are development artifacts, not mod dependencies. The manual campaign checklist in [strategic_ai.md](strategic_ai.md) remains required for runtime verification.
