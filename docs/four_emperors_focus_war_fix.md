# Gaul and Leithanien: opening war in 1029

Gaul's "Silence the Kaiser" originally only granted a wargoal. The first fix
waited for envoy refusal and ordinary native declaration legality. The requested
behavior now makes this particular AI story war mandatory and accelerates the
focus path; arbitrary wars by other countries still use normal diplomacy rules.

An AI strategy plan prioritizes the sixteen required checkpoints, in either
historical mode. A weekly watchdog completes at most one missing checkpoint with
its native rewards. Existing friendly Victoria/Ursus branches satisfy their
mutually exclusive checkpoints. The first fifteen checkpoints prepare the confrontation during 1028. The final
war focus is held until 1029.1.1, including when the envoy has already been
refused. Prepared AI Gaul completes that final focus and declares war on the first
daily pulse of 1029. Ordinary focus progress may prepare the route sooner, but
does not bypass the date gate. An old save already past that date catches up
through the same daily/weekly hooks; a war that already happened is not undone.

For AI Gaul the war focus waits for the 1029 calendar gate instead of envoy refusal or a back-down flag.
The peaceful puppet focus is available only to a human Gaul. The exact scripted
Gaul/Leithanien declaration clears their bilateral nonaggression pact and truce,
and separates them if they share a faction: a Gaul-led faction removes only
Leithanien, otherwise Gaul leaves. This is deliberately an authored declaration,
not a discretionary AI preference conditioned on grievances, confidence, reserves,
an unexpired goal or `can_declare_war_on`. An additional negative native war
preference discourages early use of an old-save wargoal before 1029. The player
controlling Gaul retains ordinary choices; this calendar enforcement targets AI.

The callback requires existing, non-capitulated countries, original AI Gaul and
an independent Gaul. It cannot resurrect annexed countries or guarantee a war
against Gaul's own puppet in a save that already completed the old puppet branch.
A successful declaration, or an already-existing war, records a persistent flag
so peace does not cause a repeated declaration. Human Gaul retains ordinary focus
and envoy choices and receives no forced focus completion or declaration. No DLC
is required for the script mechanisms used here.

Verification: the regression suite executes the actual focus graph, rewards,
weekly/daily callbacks and event AST, including the 1028.12.31 to 1029.1.1 boundary. Tests cover the full sixteen-pulse sequence,
existing friendly branches, player control, peaceful AI outcomes, shared factions,
missing participants and no repeated war after peace. These are explicit native
script fixtures, not tests of HOI4's scheduler, diplomacy engine or combat.
