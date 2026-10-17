# Dawn of Terra strategic AI

## شروع سریع

این نسخه داخل خود مود اجرا می‌شود؛ برای بازی به پایتون، API یا اتصال اینترنت نیاز ندارد. شخصیت کشورها، اعتماد و دلخوری، اعتبار بین‌المللی، خستگی جنگ و یاد شکست روی تصمیم‌های آن‌ها اثر می‌گذارد. این رفتار با اسکریپت‌های بومی HOI4 شبیه‌سازی شده است و گفت‌وگوی آزاد یا احساس واقعی یک مدل زبانی نیست.

بخش **Strategic Council** و گزارش‌های مربوط به آن از دیسیژن‌ها حذف شده‌اند تا فهرست شلوغ نشود. AI به‌صورت خودکار اجرا می‌شود و برای فعال‌شدن به دیسیژن نیاز ندارد.

بخش **The Diplomatic Desk** هم همراه با گزینه‌های دستیِ فرستادن فرستاده، بازسازی اعتماد، همکاری، خویشتن‌داری و گزارش دیپلماتیک از دیسیژن‌ها حذف شده است. دیسیژن‌های بخش **Promises and Bargaining** شامل **Offer aid** و **Offer protection** هم حذف شده‌اند. پیشنهادهای خودکار AI و قراردادهای موجود همچنان از طریق رویدادها پردازش می‌شوند؛ طرف مقابل می‌تواند رد کند یا پیشنهاد کوچک‌تر بدهد و امضای نهایی جداگانه لازم است. وعدهٔ تسلیحاتی از تجهیزات واقعی کشور ارسال‌کننده تأمین می‌شود. پذیرفتن تضمین دفاعی، به‌تنهایی فرمان ورود اجباری بازیکن به جنگ صادر نمی‌کند؛ باید پیامدهای تعهد را در انتخاب‌های عادی دیپلماسی در نظر گرفت.

برای بررسی رفتار، یک کمپین تازه شروع کن و تغییر رفتار کشورها را پس از چرخه‌های هفتگی دنبال کن. بارگذاری سیو موجود هم متغیرهای جدید را بدون پاک‌کردن حافظهٔ دیپلماتیک قبلی آماده می‌کند. فایل‌های داستان، شخصیت‌ها، فوکوس‌ها و روابط اولیهٔ سارگون پایهٔ سناریو می‌مانند.

آزمایش‌های خودکار اسکریپت جای اجرای واقعی بازی را نمی‌گیرند. نصب HOI4 در محیط توسعه موجود نیست؛ نتیجهٔ کمپین، کارایی، رفتار دقیق جبهه و سازگاری DLC باید داخل بازی بررسی شود.

## Native layers and contracts

The implementation is a collection of reversible native strategies, scripted effects, decisions and authored events. HOI4 owns battle execution, pathfinding and equipment inventories. The shared-war correction now explicitly forms factions between eligible AI governments, while player membership remains voluntary. The development interpreter executes selected script primitives for regression scenarios; it is not an HOI4 emulator.

The [global AI repair](global_ai_repair.md) documents the current economy, research, production, recruitment, fronts, air and naval changes and their validation limits. Earlier releases contained 119 regression scenarios, including the Gaul focus-war coverage. The latest [defensive coalition correction](defensive_coalition_fix.md) covers human Sargon attacking AI Bolivar and Columbia, real starting ideology permissions, the non-DLC faction path and a war-triggered check after one day. Its focused native check has zero errors. The earlier [pact correction](diplomacy_policy_fix.md) remains in effect. Evidence for the original strategic release, including its unresolved vanilla references, remains in [native_validation_strategic.md](native_validation_strategic.md).

| Layer | Source files | Behavior |
| --- | --- | --- |
| Directed diplomacy | `common/scripted_effects/terra_diplomacy.txt`, matching triggers and strategies | Separate trust, grievance and utility for each partner; ordinary diplomatic preferences. |
| Persistent strategic state | `common/{scripted_effects,scripted_triggers,ai_strategy}/terra_strategic_state.txt` | Current ruler/government profile, domestic constraints, fatigue, defeat memory, reputation and strategic priorities. |
| Security assessment | `common/{scripted_effects,scripted_triggers,ai_strategy}/terra_security.txt` | Intelligence confidence, escalation notices, perceived common danger and defensive coordination. |
| Wartime faction formation | `common/{scripted_effects,scripted_triggers}/terra_coalitions.txt`, faction template and charter | Forms and extends named factions between independent AI countries already fighting a common enemy. |
| Limited native pacts | `common/{scripted_triggers,ai_strategy}/terra_diplomacy_policy.txt` | Suppresses neutral startup pact spam; requires earned confidence and a concrete wartime use. |
| War director | `common/scripted_triggers/terra_war_director.txt`, matching AI strategies | Recovery fronts, home defense, rifle/transport demand, conditional enemy-specific opportunities and allied cooperation. |
| Concrete commitments | `common/scripted_effects/terra_commitments.txt`, matching triggers and events | Negotiated arms shipments and time-limited defensive guarantees with completion, lapse and breach handling. |

The country registry includes 35 fixed tags and D01–D50. New landless countries wait until they become valid participants. Siesta and Seaborn retain their original-tag exclusions. Ta-Netjer retains its protected military-policy treatment; it receives passive strategic state and transfers temple recruits while maintaining no standing army. Existing Sargon subjects, faction initialization and DLC safeguards remain intact.

### Persistent state

All four public numeric values are country-local and bounded to 0–100:

| Variable | Initial value | Meaning |
| --- | --- | --- |
| `terra_state_fatigue` | 0 | Accumulated war burden; prolonged offensive and civil wars cost more. |
| `terra_state_defeat_memory` | 0 | Persistent strategic trauma from capitulation. |
| `terra_state_reputation` | 50 | Credibility earned by delivered obligations and damaged by aggression or breach. |
| `terra_state_domestic_pressure` | 0 | Recomputed pressure from stability, war support, reserves, equipment, civil conflict and accumulated trauma. |

`terra_state_initialized` prevents resets on reload or repeated initialization. `terra_state_goal_security`, `terra_state_goal_recovery`, `terra_state_goal_commerce` and `terra_state_goal_revision` express one primary priority. Recovery uses different entry and exit thresholds to avoid weekly oscillation. Revision requires a foreign-held core, an imperial profile, sustainable domestic conditions and the existing military-policy exclusions.

The six existing `terra_dip_personality_*` flags are reassigned from the actual ruling character and current government each week. Known historical rulers retain their existing behavioral grounding while they are ruling under the matching government. Unknown successors fall back to the mod's actual ideology groups. Leadership changes do not clear trust, grievances, fatigue, defeat memory or reputation.

### Public callable effects

| Effect | Caller and result |
| --- | --- |
| `terra_state_initialize_effect = yes` | THIS country after diplomacy initialization; safe inside startup's global `every_country`. Initializes once. |
| `terra_state_weekly_effect = yes` | ROOT = THIS; refreshes personality, domestic pressure and priority before diplomacy scoring. |
| `terra_state_monthly_effect = yes` | ROOT = THIS; accumulates fatigue at war and allows gradual stable-peace recovery. |
| `terra_state_record_defeat_effect = yes` | Current country is the capitulated loser. Adds 40 defeat memory and 20 fatigue, with a 30-day deduplication flag. |
| `terra_state_record_aggression_effect = yes` | Current declaring country; reduces reputation by 8 and records recent aggression. |
| `terra_state_record_fulfillment_effect = yes` | Current provider after an actual obligation is fulfilled; adds 3 reputation, limited to once per 30 days. |
| `terra_state_record_breach_effect = yes` | Current provider after an actual breach; subtracts 15 reputation, limited to once per 30 days, and records an oathbreaker flag. |

Record callbacks use `terra_state_recordable`, which permits existing initialized capitulated countries. They deliberately do not require `terra_dip_ready`, because that trigger becomes false on capitulation. No callback changes autonomy, recruits units, creates equipment or rewrites a leader.

Stable peace removes 4 fatigue and 1 defeat memory monthly; unstable peace removes 2 fatigue and retains defeat memory. A damaged reputation can recover toward 50 during quiet peace once recent aggression and breach records have expired. Reputation above 50 requires credited conduct, rather than passive time.

Subject war-call and join-war preferences have an explicit high-weight native profile for each possible overlord, except for Ta-Netjer's no-army sanctuary policy. Those profiles bypass sovereign fatigue and domestic-pressure gates. [Ta-Netjer now has no army](tnj_no_army_and_subject_recruitment.md), while other subjects receive resource-gated infantry training requests; [Gaul's mandatory story route](four_emperors_focus_war_fix.md) prepares the required focuses during 1028 and launches its authored war against Leithanien at the opening of 1029. Existing forces still obey native combat and supply constraints; the scripts do not invent an army to satisfy the obligation.

### Timing, scope and conservation

`on_startup` is global. Daily, weekly and monthly hooks already execute for each country; they must not wrap the same work in an additional global country loop. Weekly scoring and threat helpers require ROOT = THIS. Targeted decisions use ROOT as actor and FROM as partner. Cross-country events preserve the two participants through explicit sender/recipient relays rather than mutable global event targets.

Intelligence confidence selects increasingly conservative estimated strength margins: greater than 1.35, 1.5 or 1.8 for high, medium or low confidence. Native army strength remains an estimate. Escalation requires a 60-day notice period, continuing motive and readiness, and native legality for declarations. An authored focus or event remains a separate scenario mechanism; the director's preference rules are not a replacement for every engine or story war path.

Aid commitments negotiate 300 infantry-equipment units or a 150-unit counteroffer. Signing creates an obligation; the weekly delivery process uses a native equipment transfer after the due date, with a grace period for insufficient stocks. It does not credit fabricated replacement equipment. Defensive terms negotiate 180 or 90 days and create a native guarantee only after final confirmation. A covered defensive war has a response window; ordinary war-entry rules remain authoritative.

## Manual campaign checks

These are scenarios to run in HOI4, not claims that in-game testing has already passed. Test a fresh campaign and an existing save, inspect `error.log`, and record the countries, DLC combination, date, active obligations and strategic state when behavior differs.

| Feature | Scenario and expected result |
| --- | --- |
| 1. Save migration and country registry | Existing diplomacy memory survives reload; released D01–D50 countries initialize separately when they become eligible. |
| 2. Ruler and regime personality | Replace a known ruler or change government; the weekly profile changes, while accumulated memories remain. |
| 3. Bilateral trust and grievances | Two different countries negotiate with the same recipient; replies and directed memories affect their own pairs. |
| 4. Domestic constraints | Lower stability, reserves and support; domestic pressure rises and discretionary escalation becomes harder. |
| 5. Fatigue and defeat | Fight a prolonged war, capitulate, then recover at peace; fatigue accumulates and defeat memory decays slowly without a startup reset. |
| 6. Strategic priority | A strained state keeps recovery until its lower exit thresholds are met; commerce and revision require their documented conditions. |
| 7. Reputation | Fulfill an actual agreement and breach another; reputation changes once for the credited callback, remains bounded and influences later evaluation. |
| 8. Intelligence uncertainty | Test La Résistance intelligence and the non-DLC fallback; low-confidence planners require a larger margin than high-confidence planners. |
| 9. Warnings and backdown | A hostile ready AI issues notice, waits through the period and backs down if the motive or readiness disappears; no missing notice should enable a director war preference. |
| 10. Shared danger | Before a common war, coordination preferences rise. Eligible independent AI countries actually fighting the same enemy can form a named faction; players and existing blocs are not enrolled. |
| 11. Counteroffers and actual aid | Negotiate both aid quantities; final acceptance, insufficient stocks, grace period and delivery conserve real equipment and cannot deliver twice. |
| 12. Defensive guarantees | Test both durations, a covered defensive war, refusal, voluntary release and annexation; only guarantees introduced by the contract are removed when it closes. |
| 13. Fronts and logistics | Empty rifle reserves while fighting several enemies; recovery priority wins over opportunistic attacks. Low spare trains/trucks alone change production demand, not global recovery. Production uses ordinary factories and technology. |
| 14. Subject loyalty | Exhaust a Sargonian subject and call it to war; obligations retain their intended preference. |

Repeat campaigns with multiple countries and several game years before treating strategy weights as balanced. Frequency, CPU cost, fronts, guarantees and equipment-selection details require native engine observation.

## Removed decision menus

Strategic Council, Promises and Bargaining, and The Diplomatic Desk no longer define decision categories
or manual actions. This removes all per-country lists added by the AI director: Open a channel, Rebuild confidence, cooperation, restraint, briefings, Offer aid and Offer protection,
including its withdrawal/release actions. Existing automatic negotiation events,
resource-conserving deliveries, deadlines and active contract cleanup remain.

Comment-only files are retained at all three old decision/category path pairs so extracting
a new ZIP over an older installation replaces the obsolete UI definitions. No
visible category is declared in those files. Restart HOI4 after updating the mod.
