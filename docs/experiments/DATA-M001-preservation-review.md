# DATA-M001 first tranche preservation review

Status: EXPERIMENTAL, visual gate **not cleared**. 2026-09-25. This is a review of the existing two TRAIN identities and their ten raw Base outputs, not an authorization to generate the remaining 100 or to train MAKEUP-001. Official dataset ACCEPT / RETRY / REJECT states remain pending project lead review.

## Inputs and method

Input: the verified first-tranche archive, 20 of 20 successful FLUX.2 Klein Base edits, no LoRA. The script [`scripts/data_m001_preserve.py`](../../scripts/data_m001_preserve.py) reads each source and raw result, checks source and raw hashes and no-adapter metadata, and uses the pinned `jonathandinu/face-parsing` SegFormer revision `758b82e15a0178c9db39c1ff666a8b56e3a550c8`. Weights SHA256: `c2bec795a8c243db71bd95be538fd62559003566466c71237e45c99b920f4b62`. CPU only. No face parser was trained.

The original portrait supplies all geometry and fine texture. Source semantic labels define skin, eyebrows and lips. Soft fields around the original eyes and cheeks transfer bounded, low frequency Lab pigment and tone from the raw output. A second pass transfers representative eyelid pigment from the generated face to the original eyelid position, not generated pixels or silhouette. The generated lip region supplies median lipstick pigment, which is applied inside the original lip labels. No raw facial texture or geometric pixels are pasted. All labels outside source skin, brows and lips are copied byte for byte from the original, including eyeballs, nose, mouth and teeth, hair, ears, neck, clothes and background. Eye and cheek boundaries feather within source skin; lip and brow boundaries feather inward.

Run: `python scripts/data_m001_preserve.py --pilot .tmp/data_m001/pilot_results --parser .tmp/data_m001/parser_model --output .tmp/data_m001/preserved_v2_complete --enhance-eyes`.

Output: 20 preserved images, 20 originals, 20 raw images, original generation sidecars, the pilot config/source manifest/plan, masks, per-image provenance and checksums, one JSON report and four sheets. All 20 processed. For all 20, `changed_outside_allowed = 0`, and the eye, nose, mouth and hair semantic labels have zero changed pixels. This proves exact pixel protection for the parser-defined regions, not that the parser segmentation or appearance quality is perfect. No GPU was used for preservation.

## Comparison sheets and data

| Identity | Styles 1 to 5 | Styles 6 to 10 |
| --- | --- | --- |
| `003025` | [Original / Raw / Preserved](../../.tmp/data_m001/preserved_v2_complete/review_sheets/003025_part_1.jpg) | [Original / Raw / Preserved](../../.tmp/data_m001/preserved_v2_complete/review_sheets/003025_part_2.jpg) |
| `054109` | [Original / Raw / Preserved](../../.tmp/data_m001/preserved_v2_complete/review_sheets/054109_part_1.jpg) | [Original / Raw / Preserved](../../.tmp/data_m001/preserved_v2_complete/review_sheets/054109_part_2.jpg) |

Full resolution and metadata: `.tmp/data_m001/preserved_v2_complete/targets/<identity>/<style>/`. Original input metadata: `.tmp/data_m001/preserved_v2_complete/input_provenance/`. JSON report: `.tmp/data_m001/preserved_v2_complete/preservation_report.json`. Downloadable local bundle: `.tmp/data_m001/data_m001_preserved_v2_complete.zip` (19,473,853 bytes). The parser weights are not included in the bundle. The preserved pixels in this bundle are hash-identical to the visually reviewed initial V2 output; only provenance packaging changed.

## Per-image visual observations

These are Codex observations, **not** official training-pair acceptance. `WEAK` means the style is not clear enough to justify an ACCEPT decision; `PARTIAL` means some style signal survives but a visible quality issue remains. No automatic metric substitutes for visual review.

| Identity | Style | Observation | Review finding |
| --- | --- | --- | --- |
| 003025 | Natural Makeup | Very slight lip and complexion change; little eye definition. | WEAK |
| 003025 | No-Makeup Makeup | Nearly indistinguishable from bare. | WEAK |
| 003025 | Soft Glam | Raw polished eye/brow look mostly lost; preserved target resembles Natural. | WEAK |
| 003025 | Smoky Glam | Dark eye makeup clearly survives with original eye shape and skin texture. Diffuse edge remains. | PARTIAL |
| 003025 | Dewy Peach | Some peach lip/eye tint, but dewy finish and blush are weak. | WEAK |
| 003025 | Rosy Pink | Distinct pink eyes and lips; upper eye pigment appears broad and somewhat mask-like. | PARTIAL |
| 003025 | Bronze / Golden Glam | Gold/ochre eye color survives, but cheek/bronze separation is limited. | PARTIAL |
| 003025 | Matte Nude | Very close to original, not a reliable matte nude class example. | WEAK |
| 003025 | Classic Red Lip | Red lipstick survives inside original lip shape; original face and scene retained. Border needs close review. | PARTIAL |
| 003025 | Bold Evening Glam | Dark eyes and plum lip survive, but lashes and sculpting from raw do not. | PARTIAL |
| 054109 | Natural Makeup | Almost no visible distinction from source. | WEAK |
| 054109 | No-Makeup Makeup | Nearly indistinguishable from bare. | WEAK |
| 054109 | Soft Glam | Eye, cheek and lip effects mostly disappear. | WEAK |
| 054109 | Smoky Glam | Dark eye area is visible; still broad rather than precisely eyelid-localized. | PARTIAL |
| 054109 | Dewy Peach | Warm eye/lip color survives weakly; luminosity and peach cheek effect mostly lost. | WEAK |
| 054109 | Rosy Pink | Clear pink eyes and lips, but broad eyelid color may look artificial. | PARTIAL |
| 054109 | Bronze / Golden Glam | Gold eye pigment visible; broad skin/cheek effect is modest. | PARTIAL |
| 054109 | Matte Nude | Almost identical to source. | WEAK |
| 054109 | Classic Red Lip | Strong red lip, but high contrast makes the lip boundary on the open-mouth smile hard and uniform. Teeth pixels remain original. | PARTIAL, lip artifact |
| 054109 | Bold Evening Glam | Smoky blue eye survives; near-black/gray lips from raw remain visually implausible and inconsistent with the other identity. | PARTIAL, lip color failure |

## Result and gate

Facial geometry, expression, hair, clothing and background are far better preserved than in raw FLUX results because they come from the original. Original skin texture largely survives, unlike raw outputs' smoothing. The price is major loss of subtle style information. Natural, No-Makeup, Soft Glam, Dewy Peach and Matte Nude are weak on at least one identity, generally both. Strong eye colors and high-contrast lips transfer more clearly but can look diffuse or uniformly filled. There are no obvious outer face-mask edges, but eye pigment can still be broad, and lipstick can look sharply bounded on an open-mouth smile. The automatic exact-pixel check does not establish visual acceptability.

No-Makeup Makeup is **not yet demonstrably learnable**. Its original pilot instruction asked for a barely perceptible result, and the preserved outputs are effectively bare. Only that style's future instruction in `data/makeup/DATA-M001/config.json` was revised to request visible but subtle complexion evening, light blush, sheer lip tint and mild brow/eye definition. The existing two No-Makeup raw results and their original prompt records have not been changed or regenerated. A future rerun of only those two would be required to assess the revised prompt.

**Recommendation:** Do **not** generate the remaining 100 or finalize any of these as accepted pairs. The preservation method needs one concrete correction: transfer subtle eye, cheek and complexion appearances with better localized intensity while retaining source texture, then review the same 20 side by side. Lip blending on open-mouth smiles should be handled in that correction, with teeth still protected. Do not broaden dataset/model work. If corrected transfer cannot make the weak classes visually distinct, address only those demonstrated style prompts or components before scaling.
