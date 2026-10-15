# Ta-Netjer's geographic home guard

The previous AI profile used an invalid `num_of_owned_states` trigger. Its troop
buffers were also preferences, not an engine-enforced national boundary. The
profile now uses a valid owned-state predicate and retains its defensive orders.

A country-scoped daily callback for original AI TNJ additionally selects an owned,
controlled home state and scans states outside TNJ ownership. Native
`teleport_armies` moves only TNJ-owned armies in those foreign states to that safe
home state. The nested state scopes make `to_state = PREV` the selected home,
not the source state or another country. Other countries' armies and TNJ units
already on TNJ-owned territory are untouched. No units, manpower or equipment are
created. Existing TNJ guards abroad are included when an old save is loaded.

The callback also installs the existing no-foreign-war rules and template lock
once for older saves. It does not end a war TNJ already joined. A human TNJ, a
capitulated TNJ or an unrelated country is not relocated. Without an owned and
controlled safe state there is no teleport or ownership/controller change.

This is daily repatriation, not a continuous engine movement lock: a unit can
cross the boundary between daily pulses. It deliberately returns such units
rather than relying solely on diplomatic access or battleplan weights. Native
pathfinding, expeditionary ownership, transport and movement during each day
still require in-game verification.

Validation on 2026-10-15: all 114 regression scenarios and asset/structure checks
passed. Six home-guard scenarios exercise the actual AST with explicit state,
army-owner and controller fixtures; twelve cover the revised Gaul route. CWTools
recognized the new geographic callback and AI plan without native errors, and
confirmed removal of the invalid guard predicate. Full native validation still
reports existing missing base-game references (including `annex_everything`) and
unrelated mod diagnostics; it is not a clean full-mod pass. Reports for this run
are retained under `/tmp/terra-tnj-gaul-fix-1-*`. HOI4 is not installed here.
