# DATA-M001 Preservation V3 review

Status: EXPERIMENTAL. Visual gate **not passed**. 2026-09-25. This is a focused correction and review of the same 20 DATA-M001 raw images, not new Base generation or Makeup training. The review states below are Codex visual assessments of V3. They do not modify the official DATA-M001 `reviews.json` or authorize dataset finalization.

## What changed

[`scripts/data_m001_preserve_v3.py`](../../scripts/data_m001_preserve_v3.py) retains the pinned CPU face parser and the original portrait as the sole geometry and fine texture source. The raw result supplies regional Lab appearance statistics only. Source aligned skin, brows and lip tissue are the only editable labels. The original eyeballs, iris, pupils, nose, inner mouth and teeth, hair, ears, neck, clothing and background are copied exactly. The new source eye field concentrates on upper eyelids with a weak lower lash allowance and suppresses broad tails. The cheek field is narrower. Eye and cheek color is measured relative to each image's own complexion, reducing contamination by raw facial reconstruction. Global complexion uses bounded median chroma and a small luminance shift, retaining original texture. Lip pigment is transferred into source lip tissue with an inward distance feather at both exterior and mouth opening. Generated lip geometry is never pasted. The lips remain somewhat too uniform in the open mouth example.

One compositor uses per style strengths for complexion, cheek, eye, lip, brow and finish. The exact table is `STRENGTH` in the script and is serialized into each target's `preservation_v3.json`. The settings range from 0.08 to 0.95, with all Lab channel shifts bounded. This is intensity control only and never enables raw pixel replacement.

Command: `python scripts/data_m001_preserve_v3.py --pilot .tmp/data_m001/pilot_results --v2 .tmp/data_m001/preserved_v2_complete --parser .tmp/data_m001/parser_model --output .tmp/data_m001/preserved_v3b`.

All 20 processed on CPU. The first invocation failed before producing any target because of an array broadcasting typo; the corrected invocation above ran into a new directory and completed 20/20. All per image V3 hashes match the report. All 20 record zero changed pixels outside parser defined editable labels and zero changed pixels in source eye, nose, mouth and hair labels. This verifies pixel protection, not style or perceptual quality. No GPU, FLUX or LoRA was loaded for this correction.

## Four way comparison

| Identity | First five styles | Last five styles |
| --- | --- | --- |
| `003025` | [Original / Raw / V2 / V3](../../.tmp/data_m001/preserved_v3b/review_sheets/003025_part_1.jpg) | [Original / Raw / V2 / V3](../../.tmp/data_m001/preserved_v3b/review_sheets/003025_part_2.jpg) |
| `054109` | [Original / Raw / V2 / V3](../../.tmp/data_m001/preserved_v3b/review_sheets/054109_part_1.jpg) | [Original / Raw / V2 / V3](../../.tmp/data_m001/preserved_v3b/review_sheets/054109_part_2.jpg) |

Full resolution quadruples, masks, generation sidecars, source manifest, pilot configuration and V2 report are in `.tmp/data_m001/preserved_v3b/`. The JSON report is `.tmp/data_m001/preserved_v3b/preservation_v3_report.json`. The downloadable local bundle is `.tmp/data_m001/data_m001_preserved_v3.zip` (27,401,493 bytes; ZIP CRC check passed, 20 each of Original, Raw, V2 and V3). No-Makeup's revised future prompt is not used in these raw outputs. The original pilot config is packaged intact.

## Per image visual gate

`ACCEPT` below means this Codex visual review found a plausible project style and source preservation. A project lead still needs to approve the actual training pair. `REGENERATE_RAW` means the raw appearance itself is unsuitable or too weak. `PRESERVATION_FAIL` means usable raw style information exists but V3 does not transfer it adequately. All V3 images keep original identity, face geometry, expression, natural skin texture, hair, clothes and background much better than raw. Parser protected eyes, nose and inner mouth are exact. The notes focus on remaining style and localization problems.

| Identity | Style | V3 visual observation | State |
| --- | --- | --- | --- |
| 003025 | Natural Makeup | Lip/complexion shifts remain too small; nearly bare. | PRESERVATION_FAIL |
| 003025 | No-Makeup Makeup | Almost bare even in raw and V3, insufficient subtle but visible class signal. | REGENERATE_RAW |
| 003025 | Soft Glam | Raw neutral eyes and polished lip largely disappear. | PRESERVATION_FAIL |
| 003025 | Smoky Glam | V3 narrows the V2 eye mask but loses too much dark smoky effect. | PRESERVATION_FAIL |
| 003025 | Dewy Peach | Warm lip visible, dewy/peach cheek and eye character weak. | PRESERVATION_FAIL |
| 003025 | Rosy Pink | Pink eyes and lips visible, narrower than V2 and separated from bare. | ACCEPT |
| 003025 | Bronze / Golden Glam | Warm gold eye and mild warm tone are visible, less mask-like than V2. | ACCEPT |
| 003025 | Matte Nude | Still indistinguishable from bare and Natural at review size. | PRESERVATION_FAIL |
| 003025 | Classic Red Lip | Clear red lip within source lip shape with preserved expression and texture; edge is acceptable in this closed-mouth source. | ACCEPT |
| 003025 | Bold Evening Glam | Dark localized eye and plum lip distinguish it from other styles without raw facial reconstruction. | ACCEPT |
| 054109 | Natural Makeup | Barely visible lip/complexion change despite obvious raw makeup. | PRESERVATION_FAIL |
| 054109 | No-Makeup Makeup | Raw itself is nearly bare; V3 cannot recover a clear class signal. | REGENERATE_RAW |
| 054109 | Soft Glam | Raw polish is mostly missing; target is close to Natural and bare. | PRESERVATION_FAIL |
| 054109 | Smoky Glam | V3 eye narrowing eliminates the mask but leaves weak smoky makeup. | PRESERVATION_FAIL |
| 054109 | Dewy Peach | Some warm lip tint, but cheek glow/peach makeup mostly lost. | PRESERVATION_FAIL |
| 054109 | Rosy Pink | Pink eye/lip effects remain visible and better confined than in V2. | ACCEPT |
| 054109 | Bronze / Golden Glam | Gold eye pigment remains visible; cheek bronzing is weak but class still distinguishable. | ACCEPT |
| 054109 | Matte Nude | Little reliable matte or nude signal survives. | PRESERVATION_FAIL |
| 054109 | Classic Red Lip | Red lip remains overly uniform and sharply bounded around the open-mouth smile. Teeth are unchanged. | PRESERVATION_FAIL |
| 054109 | Bold Evening Glam | Raw has an implausible near-black/gray lip and V3 cannot make this a valid statement lip. | REGENERATE_RAW |

Visual tally: **6 ACCEPT, 3 REGENERATE_RAW, 11 PRESERVATION_FAIL**. These are review observations, not automatic metrics or entries in the official finalizer review file. The majority of V3 targets are not acceptable; V3 **cannot be frozen**.

## Decision

V3 corrected the overly broad eye field and softened some lip edges while keeping structure and non-target pixels stable. It did not solve the core style transfer problem. The concrete remaining mechanism is **over-reduction of regional makeup to median Lab color**. Subtle styles derive much of their recognizable appearance from spatially varied eyeliner, lash definition, highlight/finish and localized blush. Median color plus a narrow feathered field discards that information; increasing one uniform strength would create masks or flatten lips again. This affects both identities and several styles, so the failures are systematic preservation failures, not isolated raw generations. The open-mouth lipstick boundary is a second specific manifestation of uniform regional lip color.

No-Makeup **requires regeneration of only its two raw targets** with the already revised future prompt, but not yet: its new raw results would still face the unsolved preservation gate. The `054109` Bold raw target would also need a bounded replacement once preservation works. Keep the six candidate accepted outputs, but do not enter official ACCEPT decisions or run the other 100. The exact next action is to correct regional appearance transfer so it retains localized eye, cheek and lip variation while source geometry/texture remain immutable, then reprocess these same 20 and obtain project lead visual approval. Do not reopen dataset/model architecture or train MAKEUP-001.
