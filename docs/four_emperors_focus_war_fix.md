# Four Emperors focus-war routing

Gaul's `LGL_wo4e_start` ("Silence the Kaiser") only created an annexation
wargoal against Leithanien. The new diplomacy director treats spontaneous wars
as optional: they require grievances, warning maturity, reserves and a confident
military advantage. Completing this story focus established none of those facts,
so an AI Gaul could keep its wargoal indefinitely without declaring war.

The focus still awards the original wargoal. For AI Gaul it additionally queues
a hidden event one day later, which checks the completed focus, Leithanien's
refusal and native declaration legality before declaring this specific war.
The weekly hook retries the same guarded effect, including for saves where the
focus was already completed. A legal temporary blocker may delay that retry;
the fix does not remove truces, existing nonaggression pacts or faction ties.

The route requires an independent, non-capitulated original Gaul and an existing,
independent, non-capitulated Leithanien. It never controls a human Gaul. Submission,
the alternative puppet focus, an already-started story war and the refusal event's
back-down choice all block execution. Backing down now records a persistent flag
and closes the war focus. Old saves cannot reconstruct a back-down choice made
before this flag existed; a completed war focus plus a live legal wargoal is the
old-save authorization. This exception is only for the authored Gaul/Leithanien
branch; other countries' arbitrary wargoals retain ordinary AI decision rules.

No DLC is required. The change grants no equipment and changes no battlefield
orders. Regression scenarios execute the actual trigger/effect/event AST and
weekly hook, with native completed-focus, wargoal and legality facts supplied as
explicit fixtures. They do not emulate HOI4's scheduler, full diplomatic legality
or combat engine. In-game verification is still required: on an AI Gaul save with
the refusal and completed focus, expect war after the one-day event, or within one
weekly tick on an existing save, provided declaration remains legal. Confirm that
human Gaul retains its wargoal without automatic declaration, and that submission
and backing down remain peaceful.

Validation on 2026-10-15:

- All 108 script regression scenarios passed, including ten focus-war scenarios
  and the existing pact/coalition coverage.
- The asset/structure validator passed with zero failures (753 scripts, 54
  localisation files, map references, 999 images and five audio tracks).
- Native CWTools validation preserved source hashes and retained its full report.
  Full-mod validation did not pass: the cloud checkout lacks base-game catalogs
  and already has unrelated diagnostics. The existing Gaul focus/event diagnostic
  counts were identical to the prior baseline, whose file hashes were verified
  against `origin/main`. The one additional native error is the new declaration's
  reference to `annex_everything`: no base-game `common/wargoals` catalog is present
  here. The unchanged focus already uses that same type. No fake wargoal definition
  or schema relaxation was added to make that check pass. The new trigger, event
  and weekly callback introduce no other native errors. Reports are retained in
  `/tmp/terra-four-emperors-20261015-{report,summary,manifest,changed}.json` for this
  environment; in-game verification remains outstanding.
