# NAILS manual-mask ceiling experiment

**Verdict: MASK_AND_MATERIAL.** Analyst-traced plate masks improve cuticle, sidewall and thumb alignment, but the same style pixels still look substantially flat or synthetic. This is a two-hand diagnostic, not a production segmentation benchmark or a reason to retrain. No production code, model, segmenter, dataset, frontend or API was modified.

## Inputs and method

- Held-out 11K Hands validation identity `0000045`: `Hands/Hand_0000763.jpg`, 1600×1200, five visible nails.
- Held-out 11K Hands validation identity `0001593`: `Hands/Hand_0000658.jpg`, 1600×1200, five visible nails with different proportions and thumb angle.
- The original JPEG bytes were verified against `source-frozen-v4/source_selection.json`. The original images normalized to 512 exactly match frozen DATA-N001 references. The finalized DATA-N001 ZIP (`d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb`), localized derivative (`d7440f1cc1a8987c48235fed36f8ff23581c17719b219fc2a7e600ad867bcf90`) and step-50 evaluation ZIP (`a0c7ec088bc648cd50dd6f4329b8f80eb76efe42764f0ff89a9cb010aa31566c`) were hash-checked before use.
- Five plate contours per hand were traced visually from enlarged *original-resolution* crops, with cuticle, sidewall and distal edge points. Coordinates are retained in [contours.json](contours.json). These are analyst annotations, not independently adjudicated clinical ground truth. They are separate from DATA-N001 and training. Masks were rasterized directly at 1600×1200.
- The current approved 512 YOLO masks were mapped back to the 1600×1200 original using the existing white-pad mapping and NEAREST mask resize. Fresh runs of `scripts/nails_segment_once.py` on both frozen 512 sources matched the approved masks **pixel for pixel** (zero mismatches), confirming they represent the current CPU inference path.
- For each renderer style, the unchanged `render_target` was invoked **once** at 512 with the union of the two masks as support. The resulting RGB proposal was mapped to the original photo once; the exact same proposal was then passed to the unchanged `composite_nails` with either the current or the manual mask. The union is used only to make proposal pixels available on the small area the current mask misses. It does not change between the A/B branches. This makes a strict *final-mask* comparison, although its fixed proposal is not byte-identical to the production renderer proposal generated from the current mask alone.
- For Red and Black, each identity's saved held-out **raw step-50 adapter output for the index fingernail** was hash-verified, inverse-mapped using the saved transform, and composited twice with the exact same RGB proposal. These outputs used the evaluated 20-step, guidance-4, seed-1977 settings. The evaluation archive does not contain raw model outputs for the other four fingers; Red/Black findings therefore cover **two index nails per style, not all ten nails**.
- The full diagnostic is reproducible with `python docs/experiments/manual-mask-ceiling-2026-09-27/run_diagnostic.py --evaluation-zip D:/Downloads/NAILS-001-LOCAL-v1-step050-evaluation.zip`. Generated images and metrics are under `data/nails/work/manual-mask-ceiling-20260927/`; `report.json` records exact hashes and outside-mask pixel checks.
- Portable evidence: `data/nails/work/NAILS-manual-mask-ceiling-evidence.zip`, 57 CRC-checked members, 28,791,768 bytes, SHA-256 `3af1323c5b6715fc004990eb4a542c80cc3256e49fad04b72d10a2a21a681b8a`.

## Mask comparison

Metrics compare each current YOLO island with its analyst-traced plate. Undercoverage is manual plate pixels missed by YOLO; overcoverage is YOLO pixels outside the manual plate. Boundary distance is symmetric mean nearest-outline distance in **original-image pixels**. These numbers are relative to the manual annotation and complement visual review.

| Hand | Nail | IoU | Precision | Recall | Undercoverage | Overcoverage | Mean boundary error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0000045 | Little | 0.707 | 0.709 | 0.997 | 0.35% | 29.12% | 3.74 px |
| 0000045 | Ring | 0.829 | 0.834 | 0.993 | 0.70% | 16.60% | 2.69 px |
| 0000045 | Middle | 0.909 | 0.941 | 0.964 | 3.65% | 5.88% | 1.08 px |
| 0000045 | Index | 0.846 | 0.850 | 0.995 | 0.48% | 15.01% | 2.13 px |
| 0000045 | Thumb | 0.707 | 0.756 | 0.916 | 8.37% | 24.40% | 3.32 px |
| 0001593 | Little | 0.856 | 0.860 | 0.994 | 0.57% | 14.04% | 1.55 px |
| 0001593 | Ring | 0.843 | 0.845 | 0.997 | 0.29% | 15.48% | 2.14 px |
| 0001593 | Middle | 0.872 | 0.894 | 0.973 | 2.70% | 10.60% | 1.90 px |
| 0001593 | Index | 0.898 | 0.904 | 0.992 | 0.78% | 9.58% | 1.31 px |
| 0001593 | Thumb | 0.811 | 0.845 | 0.953 | 4.75% | 15.50% | 2.98 px |

Across the ten nails: mean IoU **0.828**, mean precision **0.844**, mean recall **0.977**, mean undercoverage **2.26%**, mean overcoverage **15.62%**, and mean boundary error **2.28 original pixels**. The dominant error on these two hands is **painting past the actual plate**, especially flat cuticle tops and squared sidewalls. The thumbs have both overcoverage and missing plate area. The known narrow stripe on prior live Hand A (`0000000`) was not directly retested because its raw pre-composite model crops were not retained; this experiment cannot claim to fix that exact live case.

## Visual findings

The generated comparison sheets use the layout **Original | Current mask | Manual mask | Current result | Manual-mask result**, with full-hand and fingertip views. The manual boundary generally removes colored skin at the cuticle and sidewalls and rounds the plate. At full-hand scale the difference is modest; in close-ups it is clear. The free edge also aligns better, especially on the thumb, but the fixed 512 proposal sometimes leaves a pale line at the distal edge.

| Style | Same-output visual result |
| --- | --- |
| Nude Pink | Manual outline reduces the squared sticker shape and skin spill on all five nails. The color remains an even mauve/pink field with weak photographed texture on both hands. |
| French Tip | Manual outline improves the plate edge but does not change the broad, straight white band. Some tips remain too opaque and disconnected from the nail's curved distal edge. |
| Pink Ombre | Manual outline improves sidewalls/thumb, while the interior remains a simple smooth gradient; several nails read mostly as flat pink. |
| Classic Red, index only | The step-50 proposal has a visible specular highlight and more gloss than renderer fills. Manual mask rounds its silhouette and reduces cuticle/skin spill. The large uniform red area and stylized highlight remain. |
| Glossy Black, index only | Manual mask rounds the edge and removes some sidewall spill. The nail remains opaque and overly smooth, with a pale/white distal artifact on one held-out index result. |

Full-hand and close-up sheets: `data/nails/work/manual-mask-ceiling-20260927/0000045_{style}_sheet.jpg` and `0001593_{style}_sheet.jpg` for the three renderer styles; append `_index_only_sheet.jpg` for Red/Black. The manual/source/current mask PNGs are in the same directory.

## Preservation and conclusion

All **10 A/B style comparisons** (six five-nail renderer sheets and four one-nail model sheets) used the same proposal for both mask branches. The unchanged compositor produced **zero changed pixels outside each branch's selected mask**. No hand geometry or background was generated into the final image outside those regions.

**MASK_AND_MATERIAL** is supported by both hands. Better masks visibly improve nail fit, especially cuticles, sidewalls and thumb shape; they do **not** make the existing style pixels convincingly photographic. The highest-impact **next implementation change** is to make the final nail plate mask accurate at original-image resolution: segment/refine each fingertip plate and preserve that contour through final compositing. A larger YOLO `imgsz` by itself failed to solve the shape problem in the earlier Hand A check. Review that bounded change before altering the renderer or model. Better material/texture preservation remains the next separate quality task after geometry is reliable.

The diagnostic does not justify claiming that NAILS-001 is production-quality, that the known live Hand A stripe is resolved, or that all-finger Red/Black behavior was tested here. No production implementation change or retraining occurred.
