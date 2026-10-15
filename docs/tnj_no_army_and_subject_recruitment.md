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

Eligibility: AI subject, owned territory, non-capitulated, infantry technology,
at least one military factory, more than 15,000 free manpower, more than 900 spare
infantry equipment, and fewer than 24 divisions at peace or 48 at war. Original
TNJ, SST and SEA are excluded. These are ceilings for this additional request,
not hard engine caps on all recruitment. They do not guarantee instant deployment:
reinforcement demand, available factory output, equipment variants, recruitment
queues and native autonomy rules still matter. An integrated subject may deploy
its units to its overlord under the normal game rules.

Verification on 2026-10-15: 119 AST regression scenarios passed, including the
1028/1029 calendar boundary, old TNJ armies/late deployments, Vouivre's 21 starting
divisions and Minos's 15, registry-wide subject eligibility, resource gates and
peacetime/wartime thresholds. The source/asset checks passed. New script files
introduce no native schema/scope errors. Full CWTools validation still fails on
existing vanilla-catalog references and unrelated mod diagnostics; those errors
remain visible in `/tmp/terra-no-army-1029-1-report.json`. Native refunds, actual
training and campaign behavior still require HOI4 playtesting.
