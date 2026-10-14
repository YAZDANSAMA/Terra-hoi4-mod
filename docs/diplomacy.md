# Dawn of Terra diplomacy director

The all-country strategic extension is documented in [strategic_ai.md](strategic_ai.md). It adds current-ruler personality updates, domestic constraints, war fatigue and defeat memory, public reputation, staged warnings, intelligence confidence, common-threat coordination, conserved aid shipments, defensive commitments and strategic reports. This document explains the underlying directed diplomatic memory and the original dialogue layer; the extension's thresholds and checks take precedence where they augment that layer.

این سیستم داخل خود مود اجرا می‌شود. کشورها شخصیت سیاسی، حافظهٔ اعتماد و دلخوری، منافع مشترک و هزینهٔ درگیری را در تصمیم‌های دیپلماتیک خود در نظر می‌گیرند. بازیکن می‌تواند مذاکره کند و پاسخ‌هایی متناسب با وضعیت و شخصیت طرف مقابل بگیرد. این یک شبیه‌سازی رفتاری با اسکریپت‌های HOI4 است؛ احساس واقعی یا گفت‌وگوی آزاد با یک مدل زبانی نیست.

The director adds persistent political behavior to native HOI4 diplomacy. It runs in the mod's scripts, with no Python runtime, external model, API key, internet connection, or remote service. Developer validation tools outside the mod do not become game dependencies.

## Behavioral model

Each eligible country, including a human-controlled country, receives one persistent diplomatic profile on initialization. Existing scenario details guide the initial assignment; other countries choose from their government at that time rather than receive an invented permanent rivalry. A later government change does not reroll the profile.

| Profile | Initial grounding | Behavior |
| --- | --- | --- |
| Pragmatic | Columbia, whose Mark Max is described as calculating | Prioritizes credible interests, workable agreements, and manageable costs. |
| Mercantile | Rim Billiton's corporatist government | Values commercial cooperation and avoids expensive disruption. |
| Imperial | Ursus, Victoria, and Gaul | Values prestige and strategic leverage; anger does not eliminate military and political risk. |
| Guardian | Sargon and its existing United Sargon relationships | Values dependable partners, subject obligations, and security. |
| Cautious | Leithanien's internal tensions | Requires stronger incentives and tolerable risks before commitments. |
| Idealist | Sami's social-democratic government | Values trust and defensive cooperation, and reacts to coercion. |

These profiles are behavioral defaults, not new canonical lore. Victoria and Gaul already have mutual negative opinion from reparations; that existing historical relationship remains in place. The director does not rewrite leaders, focus trees, ideology definitions, starting territory, or the Sargon story.

### Directed memory

Memory is bilateral and directional: A's trust in B can differ from B's trust in A. Each valid partner has separate persistent values:

- **Trust, 0–100:** reliability and willingness to cooperate.
- **Grudge, 0–100:** remembered coercion, rejection, betrayal, or conflict.
- **Utility, −100–100:** the current assessment of cooperation and strategic risk.

The variables are `terra_dip_trust_TAG`, `terra_dip_grievance_TAG`, and `terra_dip_score_TAG`, stored on the country making the assessment. Default trust and grievance start at zero; existing faction partners and a country's overlord start with 25 trust. Victoria and Gaul each start with 35 grievance toward the other, in addition to their existing opinion modifiers.

Weekly evaluations refresh utility and the country's domestic pressure. Monthly memory changes follow the first matching condition below, with values clamped to their bounds:

| Relationship this month | Trust change | Grievance change |
| --- | --- | --- |
| At war with the partner | −2 | +2 |
| Fighting a shared war | +2 | −1 |
| Same faction or a non-aggression pact | +1 | −1 |
| Otherwise | −1 | −1 |

The two countries do not automatically mirror each other's values. Persistent memory and profiles are saved with the campaign. Timed native opinion modifiers decay independently; the expiration of an opinion modifier does not reset the stored trust or grievance.

The utility score starts at trust minus grievance, then adds the following current-state terms before clamping to −100–100. Terms can stack, including both opinion thresholds.

| Current condition | Score change |
| --- | --- |
| Same faction | +35 |
| Subject–overlord relationship in either direction | +30 |
| Shared war | +20 |
| Non-aggression pact | +10 |
| Same government | +10 |
| Opinion above 25 / above 75 | +15 / +15 |
| Opinion below −25 / below −75 | −25 / −25 |
| Peaceful neighbor when the evaluator is pragmatic or mercantile | +12 |
| Partner owns the evaluator's core territory | −30 |
| Both in factions, but in different factions | −15 |
| Recent aggressor outside the evaluator's faction | −10 |
| Partner carries the temporary oathbreaker reputation | −20 |
| War with the partner | −50 |

Domestic pressure, `terra_dip_pressure`, separately combines war (+20), stability below 40% (+35), surrender progress above 15% (+35), low manpower with more than three divisions (+25), and a very low infantry-equipment stockpile with more than three divisions (+20). It is clamped to 0–100; pressure above 49 is treated as exhaustion. Preparation and offensive support additionally check military capacity, manpower, equipment, stability, borders or cores, and native estimates of relative strength. This is a simplified political and military cost model; it does not calculate trade flows, a complete national budget, or an opponent's private thoughts.

Declaring war makes the victim remember the attacker. Attacking a trusted partner, remembered faction partner, or remembered pact partner receives a larger betrayal penalty and a temporary oathbreaker reputation. Joining a partner's war and supplying lend-lease build the recipient's trust in the helper, with per-pair timed guards against repeatedly farming the same action. Peaceful faction separation carries a smaller penalty than abandonment during a war. Annexation or absence clears relationship observation flags, so absence itself is not recorded as betrayal.

### Influence on ordinary diplomacy

Both accepted calls and unsolicited join requests share the war-help memory guard; offered and requested aid share the donor guard. The faction-departure hook clears the departing country's observations, so it does not falsely accuse the members it left; the remaining members assess its departure.

The director expresses preferences through native AI strategies. A country can prefer negotiation, friendship, commercial cooperation, restraint, defense of an ally, or hostility according to its profile, memory, and current assessment. Hostile behavior still needs a plausible interest and affordable costs. A weak or exhausted state should hesitate even when it holds a grudge.

Native engine rules remain authoritative. Strategies can change willingness; they cannot make an otherwise illegal justification, declaration, guarantee, faction invitation, or treaty legal. Decisions do not force a war, impose peace, annex territory, move armies, grant free resources or factories, or forcibly change faction membership.

## Negotiating as a player

Open **The Diplomatic Desk** in the decisions interface as an eligible sovereign human-controlled country. Each action targets a specific eligible sovereign partner:

| Action | Political-power cost | Re-enable delay |
| --- | --- | --- |
| Read the partner's position | 0 | 7 days |
| Open a channel with an envoy | 15 | 30 days |
| Rebuild confidence | 35 | 120 days |
| Propose cooperation | 40 | 180 days |
| Negotiate reciprocal restraint | 25 | 90 days |

Paid requests share an additional country-wide seven-day outbound cooldown. Requests arrive after three days; the partner's response is then chosen by its AI preferences or the receiving human player. The briefing reports the **target's assessment of the reader**, including trust, territorial disputes, blocs, pressure, personality, and common interests. Trust and grievance change immediately, while utility and pressure normally refresh weekly, so a brief can contain a recent memory change alongside the previous weekly score. It is an assessment, not a guarantee of the next reply.

Responses use authored event text selected by game conditions and profile. Outcomes include acceptance, guarded contact, a smaller cooperation counterproposal, or a respectful reasoned refusal. Refusal can cite a breach of trust, disputed territory, rival blocs or war goals, domestic pressure, or inadequate benefit. If the pair becomes invalid before delivery or signature, the exchange closes without imposing an agreement. This is structured diplomacy, not free-text chat or an LLM response; a deferred exchange does not automatically retry or create a ceasefire.

An accepted cooperation offer improves relations, memory, and diplomatic preferences. It does not transfer trade resources or factories, grant an economic bonus, or add a country to a faction. Accepted reciprocal restraint can establish a native non-aggression pact when both countries remain alive, sovereign, at peace with each other, and in compatible diplomatic circumstances. The delayed response checks the pair again instead of assuming that the situation at the time of sending still exists.

Full cooperation adds bilateral trust and goodwill; a smaller pilot returns to the initiating government for an actual accept/reject choice without an additional political-power charge. Guarded restraint opens limited channels without creating a pact. Respectful refusal does not add a new grievance merely because the offer was rejected.

Invalidated paid requests return their original political-power cost to the human sender; an unsolicited AI offer has no player-paid cost to refund. Late acceptance rechecks the relationship too. Monthly AI outreach has a 180-day cooldown for the sending country and a 90-day invitation cooldown for the human recipient. It offers a real cooperation choice rather than assuming the human accepts.

Delayed conversations retain the sender and recipient through country-event scopes, with no mutable global target shared between negotiations. Independent conversations in multiplayer must not reuse another pair's context. A player remains free to reject an offer. Requests or answers that no longer have valid countries or a legal relationship must stop safely.

## Existing mod integration

Proposal and counteroffer events put polite refusal first, so a human timeout does not silently accept a treaty or cooperation agreement. AI choices retain their weighted alternatives.

The country registry includes 31 fixed tags and the 50 restored dynamic tags, D01–D50: 81 bindings in total. Bilateral memory and partner strategies cover 79 targets after excluding SST and SEA. Participants must exist, own at least one state, and not be capitulated; both humans and AI retain data, while native AI strategies apply only to AI countries. A daily hook initializes newly eligible countries, including released states and civil-war tags. Landless, annexed, and capitulated countries do not receive active evaluations. Countries derived from Siesta or Seaborn retain the original-tag exclusions.

- **Siesta (SST):** remains uninhabited and excluded from the director. Its no-government diplomacy restrictions and Columbia's focus-authorized frontier exception remain intact.
- **Seaborn (SEA):** retains its special existing mechanics and Iberian subject relationship; it is excluded from ordinary diplomatic personalities and negotiations.
- **Ta-Netjer (TNJ):** retains the sacred-territory exception. It can retain nonmilitary director data, but the military-policy trigger excludes it from initiating war. As a starting subject it cannot use sovereign negotiations; those become possible only if it is independent and otherwise eligible.
- **Sargonian satrapies:** MSN, VVA, and TNJ keep their starting subject relationships and United Sargon faction. Existing DLC and non-DLC faction initialization and repair safeguards remain intact.
- **Dynamic civil wars:** valid D01–D50 countries can participate; original-tag exceptions continue to apply. The director does not spawn rebellions or activate the landless WSG, KTH, VNH, or SCW story countries.

The earlier `common/ai_strategy/terra_allied_cooperation.txt` gives every current partner a blanket +100 call/accept preference. Its 158 call and acceptance profiles are gated only when **both** the actor and target are director-ready, so they do not drown out trust, caution, and cost calculations. If either participant is outside the director, the old behavior remains available. New profiles preserve subject duties and favor credible defensive calls; an exhausted or deeply resentful independent ally can decline, and offensive intervention requires stronger trust and capacity. Existing help on an actual shared-war front is unchanged, and the temporary wartime access system remains available.

## Source map

Game paths below are relative to `MOD/Dawn_of_Terra/`:

| File | Responsibility |
| --- | --- |
| `common/scripted_triggers/terra_diplomacy.txt` | Participant and sovereign eligibility, pair dispatch, response thresholds, preparation, affordable war and offensive-support safeguards. |
| `common/scripted_effects/terra_diplomacy.txt` | Persistent initialization, explicit per-tag memory, scoring, domestic pressure, monthly recovery, attack and help memories. |
| `common/on_actions/terra_diplomacy.txt` | Startup, daily initialization, weekly scores, monthly memory/outreach, declaration, joining an ally, and lend-lease hooks. |
| `common/ai_strategy/terra_diplomacy.txt` | Reversible native friendship, alliance, restraint, containment, preparation, legal-war, guarantees and partner-call preferences. |
| `common/opinion_modifiers/terra_diplomacy.txt` | Timed and decaying native opinion effects, independent of persistent memory. |
| `common/decisions/categories/terra_diplomatic_desk.txt` | Sovereign player visibility and the diplomatic decision category. |
| `common/decisions/terra_diplomatic_desk.txt` | Targeted briefing, envoy, reconciliation, cooperation and restraint decisions, costs, cooldowns and delayed delivery. |
| `common/scripted_effects/terra_diplomatic_outreach.txt` | Bilateral dialogue effects, reasoned refusal dispatch and AI outreach. |
| `events/terra_diplomacy_events.txt` | Safe request routing, authored response choices, pilot counteroffers, treaty signatures, briefings, invalidation refunds and invitations. |
| `localisation/english/terra_diplomacy_l_english.yml` | Player-facing decision labels, dialogue, outcome descriptions and briefings. |
| `common/ai_strategy/terra_allied_cooperation.txt` | Existing fallback call/accept integration and unchanged shared-war front help. |

The repository's `tools/validate_diplomacy.py` is a read-only developer check and limited script regression evaluator. Run it with `python3 tools/validate_diplomacy.py`; Python is not required to play the mod.

Important retained integration points:

- `common/scripted_triggers/zzz_terra_siesta_diplomacy.txt`: war and justification restrictions.
- `common/scripted_triggers/zzz_terra_siesta_guarantees.txt`: guarantee restrictions and game rules.
- `common/scripted_effects/terra_united_sargon.txt` and `common/on_actions/terra_united_sargon.txt`: guarded Sargon faction initialization.
- `common/scripted_effects/terra_wartime_routes.txt`: existing access is preserved; only automatically introduced access is removed when a relationship ends.
- `common/on_actions/00_terra_on_actions.txt`: existing Victoria–Gaul opinion setup.

## Validation and engine limits

The implemented revision passed 42 regression tests with `python3 -B tools/validate_diplomacy.py`, including directed memories, costs, native strategy activation, refusal defaults, bilateral event relays, late-war cancellation, exact refunds, faction-departure blame and aid deduplication. The prepared read-only mod check also passed script structure, localisation, asset decoding and map-reference checks. These are development checks rather than gameplay results.

An independent native CWTools pass used source commit `b377453dee803f9258be92cfc49896d09039702d` and HOI4 schema commit `297dd69c42aabe10078a8b7ab7f2d07ee631d4ef`. Its legacy macro handling required a disposable, strictly expanded copy of parameterised calls. Four absent equipment enum entries were supplied in that copy from the schema's game-generated documentation; the schema and repository sources were not relaxed or rewritten for validation. The 12 changed mod files had zero error diagnostics. Remaining warnings concerned 32 missing vanilla event sprites and four unnecessary OR wrappers. The whole-mod pass still reports unresolved base-game references and existing content diagnostics, so it is not a passed full-mod validation.

Static checks can catch malformed scripts, unresolved internal identifiers, missing localization, incomplete registry coverage, and some scope or safeguard errors. They cannot execute HOI4's diplomacy engine or prove campaign balance. No in-game test result is claimed here. An installed copy of HOI4 is required for the checklist below.

The director simulates political personality and memory. It does not provide consciousness, genuine feelings, unrestricted human reasoning, real-time generated speech, or a replacement for the engine's military AI. Relative strength and the potential defending coalition are estimated from native triggers; this is not an oracle for all enemy capabilities or a full combined-coalition military forecast. New-war preferences require motive, affordable conditions, an existing legal war goal and the native declaration check before encouraging a declaration. Threat, tension, ideology, and special diplomacy restrictions still apply; no effect automatically declares war or grants peace.

Native strategy weights interact with engine calculations and other mod content, so the observed frequency of alliances, aggression, and negotiations requires campaign testing. Different DLC combinations and game versions can change available native actions.

## Manual HOI4 scenario checklist

Run with only the intended Dawn of Terra content enabled, use a fresh campaign as well as a saved campaign, and inspect the game's error log after loading and after triggering diplomatic events. Record country pair, date, government, memory, profile, war state, and observed response for failures.

| Scenario | Expected behavior to verify |
| --- | --- |
| New campaign and first weekly/monthly pulses | Eligible existing countries initialize once; profiles and memories stay within bounds; no repeated startup reset or diplomacy errors. |
| Friendly negotiation | Envoy and confidence-building lead to a plausible acceptance, with costs and cooldowns applied once. |
| Hostile negotiation | A distrusted or resentful state can reject; rejection does not force a treaty or start a war. |
| Conditional cooperation | A conditional response has its stated tradeoff and preserves the correct sender/recipient. |
| War begins before delivery or signature | Processing rechecks whether the pair is still valid, closes the invalidated exchange, refunds the relevant paid request, and never signs an invalid pact. |
| Reciprocal restraint | A legal accepted agreement creates the native pact; incompatible blocs, subjects, a changed war, or a vanished country cannot bypass the safeguards. |
| Cooperation and commercial ties | Relations and willingness change; no free material resources, factories, or army transfers appear. |
| Betrayal and human provocation | Coercive human actions or breaking a relevant relationship affect the correct partner's memory and later behavior; forgiveness is gradual. |
| AI invitation to a human | The invitation names the correct country; accepting and declining work; the cooldown prevents repeated popups. |
| Concurrent multiplayer conversations | Two human senders negotiating with the same AI receive their own outcomes; no shared temporary target mixes up the pairs. |
| Save and reload | Trust, grudges, profile, treaty state, cooldowns, and pending responses remain coherent; no duplicate invitations or reset personalities. |
| Annexation while a response is pending | Response aborts safely; no references apply to an unrelated replacement country. |
| Landless or later released country | It receives no active diplomacy while landless and initializes when it becomes a valid participant. |
| Dynamic civil-war tag | An eligible D01–D50 participant evaluates partners correctly; original SST/SEA derivatives keep their exclusions. |
| Sargon, with and without faction-template DLC | SGN remains the existing faction leader; MSN/VVA/TNJ remain subjects; no independent or foreign-faction country is dragged into United Sargon. |
| TNJ, SEA, and SST exceptions | TNJ is not directed toward starting war; SEA/SST do not receive ordinary director interactions; Siesta's focus-only war exception is preserved. |
| Subject obligation and defensive ally call | Subjects support their duties and credible defense; costly discretionary intervention is not universally accepted. |
| Shared-war front and access | Existing ally front help works once partners actually share a war; ending it removes only access the wartime system created. |
| Weak army or exhausted economy | Hostile opinion alone does not guarantee escalation; poor manpower, equipment, stability, surrender progress, or ongoing wars reduce enthusiasm. |
| Peace and recovery | Wartime pressure and temporary hostility change appropriately; monthly memory recovery does not erase every grievance instantly. |
| Illegal war or blocked game rule | Same-ideology/threat/tension restrictions and blocked justification/guarantee rules remain enforced. |

Use several countries and multiple campaign years before treating the diplomatic weights as balanced. The checklist is a testing plan, not a record of tests already completed.
