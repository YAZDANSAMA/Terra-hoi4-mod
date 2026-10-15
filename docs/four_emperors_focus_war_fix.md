# Mandatory Gaul AI war route

Gaul's "Silence the Kaiser" originally only granted a wargoal. The first fix
waited for envoy refusal and ordinary native declaration legality. The requested
behavior now makes this particular AI story war mandatory and accelerates the
focus path; arbitrary wars by other countries still use normal diplomacy rules.

An AI strategy plan prioritizes the sixteen required checkpoints, in either
historical mode. A weekly watchdog completes at most one missing checkpoint with
its native rewards. Existing friendly Victoria/Ursus branches satisfy their
mutually exclusive checkpoints. With viable participants the route therefore
reaches the war within sixteen weekly pulses (at most 112 days); ordinary focus
progress can shorten this. An already-completed war focus is handled on the next
weekly pulse, and its ordinary completion event still checks after one day.

For AI Gaul the war focus no longer waits for envoy refusal or a back-down flag.
The peaceful puppet focus is available only to a human Gaul. The exact scripted
Gaul/Leithanien declaration clears their bilateral nonaggression pact and truce,
and separates them if they share a faction: a Gaul-led faction removes only
Leithanien, otherwise Gaul leaves. This is deliberately an authored declaration,
not a discretionary AI preference conditioned on grievances, confidence, reserves,
an unexpired goal or `can_declare_war_on`.

The callback requires existing, non-capitulated countries, original AI Gaul and
an independent Gaul. It cannot resurrect annexed countries or guarantee a war
against Gaul's own puppet in a save that already completed the old puppet branch.
A successful declaration, or an already-existing war, records a persistent flag
so peace does not cause a repeated declaration. Human Gaul retains ordinary focus
and envoy choices and receives no forced focus completion or declaration. No DLC
is required for the script mechanisms used here.

Verification: the regression suite executes the actual focus graph, rewards,
weekly callback and event AST. Tests cover the full sixteen-pulse sequence,
existing friendly branches, player control, peaceful AI outcomes, shared factions,
missing participants and no repeated war after peace. These are explicit native
script fixtures, not tests of HOI4's scheduler, diplomacy engine or combat.
