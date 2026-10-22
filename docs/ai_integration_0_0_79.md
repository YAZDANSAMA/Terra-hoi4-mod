# Terra 0.0.79 integration

Base: `95626e6661f094a84382ff63684f3e9615cf2e8c` (Columbia update v2.2).
Local input: the attached `Dawn_of_Terra(8).zip`, descriptor version
`0.0.78-reciprocal-access`, SHA-256
`0239ae5b11de0baf224d5aee496379fe85a57cdf80d34f3e894e212e1b5b6f5c`.

The archive contains every baseline main-mod file. Its 27 changed or added
files do not overlap Columbia's 92 changed or added files. The integration
preserves Columbia's entire update, including Siesta, event UI and map edits,
and keeps the separate music addon. Both descriptors use `0.0.79-merged`.

Imported changes cover development, recruitment, equipment production,
industrial research, infrastructure and common-enemy access scripts. Native
AI still pays normal costs and chooses assignments. Only three NAI defines
are overridden: infrastructure construction priority 0.45, supply buildings
12 and railways 14. Iberia's 15 flag files retain the corrected bottom-left
TGA origin.

The access dispatch and common-front registry also include Columbia's new
`SIS` tag. This only extends the existing policy to the newly registered
country; a source regression check guards registry coverage.

Source regression tests and byte comparisons validate this integration.
They do not run HOI4. Common-enemy AI-to-AI ground access was reported as
nonfunctional; the access scripts are preserved, and this merge does not
claim to fix that runtime issue.
