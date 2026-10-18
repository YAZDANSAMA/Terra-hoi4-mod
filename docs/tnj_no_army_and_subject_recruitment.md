> Historical implementation notes. The custom AI and its test counts below were retired.
> See [the current native AI baseline](native_ai_baseline.md) for active behavior and validation.

# Ta-Netjer without an army; recruitment for other subjects

The requested sanctuary policy now removes Ta-Netjer's ten guards completely.
Its starting OOB has no templates or divisions. The former home-guard AI file,
state buffers, teleporting callback, localization and geography tests are removed.

`terra_tnj_no_army_effect` is country-scoped and applies only to the existing TNJ
with original tag TNJ. It disbands its divisions, refunding real resources through
HOI4's native disband behavior, and installs its country/template restrictions
once. A daily check handles existing saves and any deployments that finish from
an old training queue. It neither scans states nor moves armies. Other countries'
units are untouched. A small AI profile suppresses new TNJ infantry demand;
general Terra military profiles/templates already exclude original TNJ.

The earlier temple manpower spirits, reserves, state populations and monthly
transfers to Sargon and Minos remain. Removing TNJ's army does not remove TNJ or
change ownership, its subject relationship or the other countries' OOBs.

The existing explicit infantry training request applied only to countries with
zero divisions. Subjects with an initial army had no equivalent peacetime request.
The new subject profile requests normal infantry training even after their first
army, with positive division demand and one forced native training request. It
uses normal recruitment, production and training costs; no units or equipment are
granted and no subject's country-wide template lock is removed.

Current eligibility: AI subject, owned territory, non-capitulated, infantry
technology, sufficient spare manpower, production or stored/received weapons,
and room in a country-sized
training goal. A domestic military factory is no longer required to train with
received equipment. The [global AI repair](global_ai_repair.md) replaces the former
15,000-man/factory requirement and fixed 24/48 request thresholds with a shared
reserve calculation and territory/industry budget. Original TNJ, SST and SEA are
excluded. The goal limits this additional request, not native recruitment. These requests do not guarantee instant deployment:
reinforcement demand, available factory output, equipment variants, recruitment
queues and native autonomy rules still matter. An integrated subject may deploy
its units to its overlord under the normal game rules.

Historical verification on 2026-10-15 (before the global repair): 119 AST regression scenarios passed, including the
1028/1029 calendar boundary, old TNJ armies/late deployments, Vouivre's 21 starting
divisions and Minos's 15, registry-wide subject eligibility, resource gates and
peacetime/wartime thresholds. The source/asset checks passed. New script files
introduce no native schema/scope errors. Full CWTools validation still fails on
existing vanilla-catalog references and unrelated mod diagnostics; those errors
remain visible in `/tmp/terra-no-army-1029-1-report.json`. Native refunds, actual
training and campaign behavior still require HOI4 playtesting.

The [recruitment stall correction](infantry_recruitment_fix.md) retires the old
profile that canceled basic infantry roles during shortages. Rifle producers may
request training while equipment is still being produced; industry-free subjects
still need received stock for the extra request. This is not a claim that native
queues, actual delivery or in-game deployment have been verified.
