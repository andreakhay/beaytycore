# Original-resolution Nails plate geometry, 2026-09-27

**Outcome: useful but limited geometry improvement.** The final mask is now built in the uploaded image's coordinate space from five source-resolution fingertip ROIs. On two held-out 1600×1200 hands, mean skin overcoverage fell from **15.62% to 11.31%**, mean boundary error from **2.28 to 1.85 original pixels**, and mean IoU rose from **0.828 to 0.851** against the prior analyst contours. Mean undercoverage rose from **2.26% to 4.48%**. The correction helps cuticles, sidewalls, and thumb outline but is not a complete nail-plate solution; material realism is unchanged.

## Implementation and reproduction

- The existing `mnemic/nails_seg_yolov8` checkpoint is unchanged (SHA-256 `99b7d1c6ceb4bde32d80fe7ae8c8eb809c27d99b55cf9db54b6692afe68f4070`). The 512 YOLO path and the model's 512 crop preprocessing are unchanged.
- Each coarse nail island is assigned to one MediaPipe fingertip. A square ROI centered on that island is cropped directly from the original image, with side `max(120, 3.5 × island long side)` original pixels, clamped to image bounds. All ROIs run in one isolated YOLO process with the existing confidence `.25`, `imgsz=640`, and `retina_masks=True`. The ROI path retains the predicted raster (`result.masks.data`), selecting the instance with greatest overlap against the coarse finger anchor; it never converts that raster through `masks.xy` and `fillPoly`.
- A 3×3 close fills small edge gaps. An original-resolution signed-distance blend (`0.75 × coarse + 0.25 × ROI`, threshold 1 original pixel) limits false expansion and rounds the legacy contour. This conservative weighting was chosen after ROI-only masks visibly missed some distal nail tips; a GrabCut trial worsened mask metrics and was discarded. Candidate ROI overlap, per-nail area ratio, component count, aspect, size, fingertip assignment, and cross-finger overlap are checked. Unreliable geometry returns a retake message.
- Renderer and model style proposals still use existing code and settings. The final `composite_nails` receives the refined original-resolution plate mask and its existing inward 1.2-pixel antialiasing. The 512 proposal support includes the refined plate where it extends beyond the old coarse island. No material/palette/model change was made.
- Reproduce with `python docs/experiments/nails-highres-geometry-2026-09-27/diagnose.py` after the prior [manual-mask diagnostic](../manual-mask-ceiling-2026-09-27/RESULTS.md) has supplied its local originals. [report.json](report.json) retains all per-nail metrics and phase timings. The manual contours were used only for evaluation, never at runtime.

## Old → refined automatic masks versus manual contours

| Hand | Nail | IoU | Overcoverage | Undercoverage | Boundary error |
| --- | --- | ---: | ---: | ---: | ---: |
| 0000045 | Little | .707 → .763 | 29.12 → 23.30% | .35 → .66% | 3.74 → 2.75 px |
| 0000045 | Ring | .829 → .845 | 16.60 → 13.27% | .70 → 2.94% | 2.69 → 2.35 px |
| 0000045 | Middle | .909 → .896 | 5.88 → 3.41% | 3.65 → 7.45% | 1.08 → 1.34 px |
| 0000045 | Index | .846 → .872 | 15.01 → 10.76% | .48 → 2.55% | 2.13 → 1.62 px |
| 0000045 | Thumb | .707 → .743 | 24.40 → 17.58% | 8.37 → 11.75% | 3.32 → 2.62 px |
| 0001593 | Little | .856 → .857 | 14.04 → 10.69% | .57 → 4.57% | 1.55 → 1.46 px |
| 0001593 | Ring | .843 → .878 | 15.48 → 10.75% | .29 → 1.78% | 2.14 → 1.53 px |
| 0001593 | Middle | .872 → .884 | 10.60 → 7.08% | 2.70 → 5.25% | 1.90 → 1.67 px |
| 0001593 | Index | .898 → .921 | 9.58 → 6.29% | .78 → 1.80% | 1.31 → .90 px |
| 0001593 | Thumb | .811 → .851 | 15.50 → 10.00% | 4.75 → 6.03% | 2.98 → 2.26 px |
| **Mean** | **10 nails** | **.828 → .851** | **15.62 → 11.31%** | **2.26 → 4.48%** | **2.28 → 1.85 px** |

Mean precision improved `.844 → .887`; mean recall decreased `.977 → .955`. Eight of ten nails improved IoU. The `0000045` middle nail regressed; the little nail of `0001593` was nearly unchanged. Both thumbs have rounder outlines and less skin spill, but the more inward edge clips some real plate at their tips. This prevents claiming the thumb issue is fully solved. The separate prior live Hand A (`0000000`) narrow stripe was not validated with a saved raw model crop.

## Visual and preservation review

Each [hand 0000045 Nude Pink sheet](0000045_nude_pink_sheet.jpg) and [hand 0001593 French Tip sheet](0001593_french_tip_sheet.jpg) includes Original, old mask, refined automatic mask, manual diagnostic mask, old composite, and refined composite at full-hand and fingertip scale. The other eight style sheets follow the same naming convention in this directory. All three renderer styles were compared on all five nails of both hands using the **same RGB proposal** for old and refined mask variants. The refined outline removes visible squared cuticle and sidewall paint, especially on the little/index nails and thumbs. Nude Pink remains uniform, French tips remain mechanically straight, and Ombre remains smooth/flat: geometry alone does not fix material.

For Classic Red and Glossy Black, the saved step-50 raw output covers only each hand's **index nail**. The two same-output model sheets per style show a rounder boundary and no material improvement; one white distal artifact remains. No new GPU generation was run, and no all-finger model-quality claim follows from these sheets. The production model branch has a focused synthetic final-mask test, but live GPU A/B was unavailable in this task.

All ten A/B style comparisons changed **zero pixels outside the selected final mask**. The unchanged compositor's inward edge still prevents polish from bleeding outside that mask. Six full production renderer requests on the two hands completed with no retakes; average wall time was **12.87 s**, including about **6.68 s** for the new ROI stage and about **5.7 s** for existing coarse YOLO. This is a CPU measurement on this workstation, not Kaggle GPU timing. `python -m pytest tests -q` from `backend/` passed **112 tests**.

The correction is sufficient to advance to a *separate material-quality review on these two hands*, not to mark arbitrary photos or all-finger Red/Black demo quality verified. More aggressive shrinkage would reduce skin spill further but worsen missing nail plate. No material, model, training, frontend, API, Hair, or Makeup changes were made.
