# DATA-M001 global V2 visual review

Status: **TECHNICALLY COMPLETE; VISUAL GATE FAILED** (2026-09-25). This is a review of the Project Lead's single bounded prompt-refinement pass, not a new dataset method or authorization for more generation. The Project Lead described the downloaded results as "hideous." The observations below are Codex's visual assessment; the official `reviews.json` remains `PENDING` for all 20 cells. No image is promoted to a training pair by this document.

## Provenance and technical checks

The downloaded `data_m001_global_v2_results.zip` is 8,219,909 bytes, SHA256 `078bc9591fe6e33e3b9fe60428aab64d49aa86b9ba18b99300e4b10e403d1df7`, with ZIP CRC passing. It is retained locally at `F:/HAIR/.tmp/data_m001/data_m001_global_v2_results.zip`; extracted files are under `F:/HAIR/.tmp/data_m001/global_v2_results_review/`. The existing verifier reported 20 attempted, 20 successful, zero failed, matching source and target hashes, and 1,185.88 seconds of summed generation time. The Kaggle record reports Tesla T4, Diffusers 0.40.0, the pinned `black-forest-labs/FLUX.2-klein-base-4B` revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, 512 × 512, 20 steps, guidance 4.0, seed 1977, FP16/CPU offload, and **no LoRA**. Model load was 131.62 seconds. The first and second global pilots used the same original portraits, model and inference settings; the V2 prompts were the controlled change. Technical success verifies execution and provenance, not visual suitability.

The original, V1 and V2 outputs for all ten styles are in the two comparison sheets:

- [Identity 003025 comparison](../../.tmp/data_m001/global_v2_results_review/review_sheets/global_v1_v2_003025.jpg)
- [Identity 054109 comparison](../../.tmp/data_m001/global_v2_results_review/review_sheets/global_v1_v2_054109.jpg)

The V2 ZIP also retains all 20 full-resolution targets, originals, per-image records, pending review structure and its own two review sheets. The local [technical audit](../../.tmp/data_m001/global_v2_results_review/technical_audit.json) records the reproducibility check. These are private research images; source-photo attribution and reuse constraints remain in the DATA-M001 source manifest.

## Visual review by style

| Style | Identity 003025 | Identity 054109 |
| --- | --- | --- |
| Natural Makeup | Somewhat less wholesale repaint than V1, but eyes, brows and lip or mouth appearance still shift from the original. | Smooth, stylized face with changed brow, eyes and lips; not a faithful subtle edit. |
| No-Makeup Makeup | Changed from V1's nearly invisible look to a doll-like reconstructed face with altered eyes, nose and mouth. | Blush is visible, but the face is plastic-smoothed and reconstructed. |
| Soft Glam | Heavy, block-like brows and altered eyes/lips persist. | Stylized smooth face and changed eye/brow/lip appearance persist. |
| Smoky Glam | Dark cosmetic area remains an oversized eye mask rather than bounded smoky shadow. | Broad charcoal region extends beyond the eyelids with a thick brow. |
| Dewy Peach | Less global reconstruction than V1, but fluorescent peach/orange eye and cheek patches are implausible. | Better apparent face retention than V1, but bright peach/pink patches remain under the eyes. |
| Rosy Pink | Pink rings around the eyes remain, rather than plausibly localized eye/cheek cosmetics. | Broad pink eye and cheek pigment remains mask-like. |
| Bronze / Golden Glam | Gold pigment remains too broad around and below the eyes. | Metallic eyelids and retouching remain strong; the cheek effect is weaker than the intended coordinated look. |
| Matte Nude | Severe mannequin-like smoothing and facial reconstruction remain. | The face is again unusually smooth and reconstructed, so matte finish cannot be cleanly separated from texture loss. |
| Classic Red Lip | Red is visible, but the mouth contour is exaggerated and hard. | A hard lipstick outline reads like a decal around the open smile and teeth. |
| Bold Evening Glam | Less black lip than V1, but a dramatic eye patch and altered facial details remain. | Dark purple eye/cheek patch and glossy dark lip accompany changed face/lighting. |

The revised prompt sometimes reduced whole-face or scene repainting and increased cosmetic visibility. It did **not** consistently preserve the original person's facial geometry or yield plausibly localized makeup. For the deliberately subtle classes, more visible makeup often came with worse face reconstruction. For the stronger classes, pigment commonly formed oversized patches or hard mouth boundaries. The two identities are a small sample; these observations establish failure of this bounded pilot, not a universal claim about every possible FLUX prompt.

## Gate and next action

This pass does **not** provide a defensible ten-style set of training targets. The repeat failures on both identities make another 100-image run unjustified under the current ACCEPT criteria. There are zero official `ACCEPT` decisions in `reviews.json`; do not mislabel these 20 technical successes as accepted DATA-M001 pairs. Do not run `--phase remaining`, finalize DATA-M001, train MAKEUP-001, or connect real Makeup inference to the UI.

The bounded prompt-only hypothesis failed: wording alone did not sufficiently constrain global Base editing to cosmetic appearance while retaining identity and facial geometry. That is the concrete blocker for the approved global-only path. Preservation, compositing and inpainting were explicitly closed by the Project Lead, so no alternative method is initiated here. Further progress requires an explicit Project Lead decision on the quality gate or authorization for a materially different input/target method; accepting visibly unsuitable targets silently would undermine the training and held-out comparison.
