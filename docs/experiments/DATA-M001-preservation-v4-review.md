# DATA-M001 Preservation V4 review

Status: EXPERIMENTAL. Practical freeze gate **failed**. 2026-09-25. This is the final targeted review of the same 20 pilot raw images. No new Base images were generated and no Makeup model was trained. The states here are Codex visual assessments, not official training-pair approvals in `reviews.json`.

## Method and configuration

[`scripts/data_m001_preserve_v4.py`](../../scripts/data_m001_preserve_v4.py) uses the pinned CPU `jonathandinu/face-parsing` SegFormer, SHA256 checked. The original portrait is the sole geometry and texture source. Raw FLUX is converted to LAB and used only to derive bounded, spatially varying appearance differences. On skin, broad Gaussian-smoothed raw-minus-original differences transfer low-frequency tone and chroma, and a separate cheek field transfers the local residual after removing global face-tone bias. Each raw eye appearance field is aligned to the corresponding source eye semantic box, with the raw eyeball inpainted in the *reference field* before smoothing so a shifted iris cannot be stamped into skin. Each upper/lower raw lip appearance field is aligned separately to the original upper/lower lip semantic box. The maps are smoothed and channel-clipped, then applied to original LAB only under source-defined, feathered makeup masks. No raw image pixel or facial geometry is pasted. One compositor has per-style complexion, cheek, eye, lip, brow, and finish strengths in `STRENGTH`; the values and hashes are stored per target.

Editable source labels: facial skin, brow tissue, upper/lower lip tissue. Periocular weights derive from parser eye adjacency and brow bounds. Cheek weights use source face geometry. Lip weights attenuate inward at outer and inner boundaries. Protected source labels include eye/iris/pupil, nose, inner mouth and teeth, hair, ears, neck, clothing and background. All protected pixels are finally copied exactly from the original. The method preserves original high-frequency skin/lip texture but does not guarantee that the appearance difference is cosmetic rather than a raw reconstruction artifact.

Run: `python scripts/data_m001_preserve_v4.py --pilot .tmp/data_m001/pilot_results --v2 .tmp/data_m001/preserved_v2_complete --v3 .tmp/data_m001/preserved_v3b --parser .tmp/data_m001/parser_model --output .tmp/data_m001/preserved_v4b`.

The first V4 output directory exposed a generated-eyeball transfer artifact. The code was corrected to exclude/inpaint the raw eyeball in the *appearance reference*, and the definitive run used a fresh `preserved_v4b` directory. The first run is not the reviewed V4 output. The corrected run processed 20/20 on CPU. Independent recomputation from saved Original, V4 and allowed masks found zero protected changed pixels for all 20; all V4 image SHA256s matched the report. The source eye, nose, mouth and hair parser labels also recorded zero changed pixels. Four comparison sheets were generated.

Exact style strengths are in the script and each `preservation_v4.json`. As examples, Natural uses complexion 0.42, cheek 0.56, eye 0.50, lip 0.48; Smoky uses eye 0.93 with complexion 0.29; Classic Red Lip uses lip 0.92 with eye 0.22. All channels are additionally capped, so a strength value never enables raw structure replacement.

## Five-way comparison and artifacts

| Identity | Styles 1 to 5 | Styles 6 to 10 |
| --- | --- | --- |
| `003025` | [Original / Raw / V2 / V3 / V4](../../.tmp/data_m001/preserved_v4b/review_sheets/003025_part_1.jpg) | [Original / Raw / V2 / V3 / V4](../../.tmp/data_m001/preserved_v4b/review_sheets/003025_part_2.jpg) |
| `054109` | [Original / Raw / V2 / V3 / V4](../../.tmp/data_m001/preserved_v4b/review_sheets/054109_part_1.jpg) | [Original / Raw / V2 / V3 / V4](../../.tmp/data_m001/preserved_v4b/review_sheets/054109_part_2.jpg) |

All full-resolution five-way groups, mask PNGs, parser labels, exact pilot config, raw generation sidecars, source manifest, V2/V3 reports, and SHA256 records are at `.tmp/data_m001/preserved_v4b/`. The consolidated report is `preservation_v4_report.json` there. The reviewed bundle is `.tmp/data_m001/data_m001_preserved_v4.zip`.

## Per-image visual classification

Every V4 result keeps source facial geometry, expression, natural texture, hair, clothing and background, with original eyeball, nose and inner-mouth pixels. The classifications below judge style fidelity, separation, cosmetic localization, lips, and visible artifacts in the full-resolution images. `ACCEPT` means plausible as a V4 candidate, pending project-lead approval. `REGENERATE_RAW` means absent or unusable source makeup information. `PRESERVATION_FAIL` means the raw has usable appearance that V4 did not transfer cleanly.

| Identity | Style | V4 observation | State |
| --- | --- | --- | --- |
| 003025 | Natural Makeup | Subtle complexion/lip change remains too close to bare; raw has more defined eyes and lip. | PRESERVATION_FAIL |
| 003025 | No-Makeup Makeup | Raw itself is nearly bare; revised future prompt has not been run. | REGENERATE_RAW |
| 003025 | Soft Glam | Raw eye and cheek polish largely disappear; target overlaps Natural. | PRESERVATION_FAIL |
| 003025 | Smoky Glam | Dark eye appearance is visible but forms a hard eye ring and extends implausibly below the eye. | PRESERVATION_FAIL |
| 003025 | Dewy Peach | Warm lip survives; dewy cheek and eye effects remain faint. | PRESERVATION_FAIL |
| 003025 | Rosy Pink | Strong pink survives, but the lower eye/cheek boundary is mask-like and less natural than V3. | PRESERVATION_FAIL |
| 003025 | Bronze / Golden Glam | Gold around and below both eyes forms a conspicuous eye mask; cheek bronze is secondary. | PRESERVATION_FAIL |
| 003025 | Matte Nude | Near-bare; matte finish and nude lip are not distinct. | PRESERVATION_FAIL |
| 003025 | Classic Red Lip | Red survives but spatial transfer makes the lip mottled orange/red with a hard upper boundary; V3 was cleaner. | PRESERVATION_FAIL |
| 003025 | Bold Evening Glam | Strong eye ring resembles a mask; lip is patchy gray/plum. V3 was more plausible. | PRESERVATION_FAIL |
| 054109 | Natural Makeup | Very slight eye/lip change, not a clear everyday makeup target. | PRESERVATION_FAIL |
| 054109 | No-Makeup Makeup | Raw still lacks a visible, distinct no-makeup look. | REGENERATE_RAW |
| 054109 | Soft Glam | Eye/lip polish from raw is largely absent in V4. | PRESERVATION_FAIL |
| 054109 | Smoky Glam | Dark eye shadow and liner are visible without a broad facial mask; source face and smile remain intact. | ACCEPT |
| 054109 | Dewy Peach | Lip tint survives, but peach cheek/highlight and dewy finish are too weak. | PRESERVATION_FAIL |
| 054109 | Rosy Pink | Pink eye, cheek and lip effects remain distinct and plausibly localized; source smile/teeth preserved. | ACCEPT |
| 054109 | Bronze / Golden Glam | Restrained gold eye and warm cheek effect remain plausible and distinguishable. | ACCEPT |
| 054109 | Matte Nude | Makeup effect is too weak to distinguish reliably from bare. | PRESERVATION_FAIL |
| 054109 | Classic Red Lip | Bright red lip remains flat and sharply bounded around open-mouth smile; teeth are unchanged. | PRESERVATION_FAIL |
| 054109 | Bold Evening Glam | Raw has an implausible near-black/gray lip; V4 cannot create a valid statement lip from it. | REGENERATE_RAW |

Tally: **3 ACCEPT, 3 REGENERATE_RAW, 14 PRESERVATION_FAIL**. The 16 to 18 usable-target practical gate was not met. Several V3 candidates became worse in V4, confirming that V4 must not be assumed superior or frozen.

## Concrete blocker and next action

The blocker is **non-cosmetic structure contamination in the spatial raw-minus-original field**. Raw FLUX reconstructs eyes, brows, lip edges and facial lighting. Even after semantic alignment, eyeball exclusion, smoothing and bounds, a local difference map cannot reliably tell an eyeliner or highlight from a shifted eyelid, ocular shadow, lip shape, or changed illumination. Increasing transfer strength makes eye rings and uneven lipstick; reducing it erases subtle styles. This is systematic across both identities and multiple styles, not isolated bad raw generations. The source pixel invariant remains true but cannot resolve this ambiguity.

V4 **cannot be frozen**. The exact known raw replacements are No-Makeup Makeup on `003025` and `054109`, using the revised future prompt, plus Bold Evening Glam on `054109`. Do not regenerate those yet, because preservation has not passed on the existing usable raw images. Stop the remaining 100 targets and MAKEUP-001 training. The immediate handoff is a project-lead decision on this one demonstrated blocker: a stronger source-anchored cosmetic correspondence or manually controlled target editing is required before DATA-M001 can scale. Do not reopen dataset source, architecture or model scope as an inferred workaround.
