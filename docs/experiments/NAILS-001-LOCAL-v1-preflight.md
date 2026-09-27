# NAILS-001-LOCAL-v1: localized retraining preflight

**Historical preflight record.** The subsequent step-50 training and held-out visual review are documented in the [evaluation](NAILS-001-LOCAL-v1-step050-evaluation.md). The approved DATA-N001 and original step-25 checkpoint remain intact. Hair, Makeup, the deployed app, nail segmentation, and the nail-only compositor were not changed.

## Frozen input and derived pairs

- Approved parent: `data/nails/work/DATA-N001-final.zip`, SHA-256 `d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb`.
- Localized derivative: `data/nails/work/DATA-N001-LOCAL-v1-candidates.zip`, SHA-256 `d7440f1cc1a8987c48235fed36f8ff23581c17719b219fc2a7e600ad867bcf90`, 68,588,461 bytes. This uses only approved DATA-N001 source, mask, target, caption, landmarks and identity split.
- The 20 identities retain 16 train and 4 validation members. Of 100 visible approved nail components, 86 support an isolated fingertip crop with context; 14 were excluded because a neighboring nail enters every acceptable crop. Each retained nail yields all five styles: **430 pairs, 340 train and 90 validation**, balanced at 68/18 per style. No validation identity enters training.
- For each retained nail, reference and target are literal matching rotated/cropped/upscaled regions of the approved source and styled target. The output has the full nail, cuticle, fingertip and nearby skin. Crop source side is 52–84 pixels, then bicubic upscaled to 512×512. The source target is not rerendered. The manifest records exact hashes and inverse mapping.
- Orientation uses MediaPipe DIP-to-tip direction matched uniquely to the reviewed nail-mask island. The tip is rotated toward image-up (observed absolute rotations 100.4°–179.8°). A crop is shrunk only to exclude neighboring nail pixels and five-source-pixel interpolation support; otherwise the finger is excluded.

| Area in 512×512 image | Mean | Median | Min | Max |
| --- | ---: | ---: | ---: | ---: |
| Original full-hand nail mask, all 100 pairs | 0.786% | 0.730% | 0.602% | 1.194% |
| Original full-hand nail mask, 80 train pairs | 0.793% | 0.719% | 0.602% | 1.194% |
| Localized nail mask, 340 train pairs | 11.252% | 11.431% | 4.321% | 20.047% |
| Localized nail mask, all 430 pairs | 11.295% | 11.431% | 4.321% | 20.047% |
| Localized changed RGB pixels, all 430 pairs | 15.975% | 16.295% | 7.002% | 28.236% |

The mean training nail area rose about **14.2×**. Twenty-one of 430 crops have 1–3 changed pixels beyond four-source-pixel transformed nail support (25 total), from bicubic edge interpolation. The original approved full-hand targets remain pixel-identical outside their masks.

## Visual and technical review

Twenty identity overview sheets were reviewed, with one held-out sheet also inspected at full resolution. Every sheet is hashed in the [review record](NAILS-001-LOCAL-v1-data-review.json). Crops, finger orientation, and all five approved styles are visible. Enlarged 512×512 source nails expose blocky mask edges and soft detail, particularly on solid colors. Acceptance is **for one controlled learning experiment**, not a claim that targets or model outputs are production quality. The 14 excluded nails are recorded per identity. The reviewer must judge any generated output against the approved target, especially French Tip, Pink Ombre and Nude Pink.

Archive SHA/CRC, member hashes, captions, frozen identity split, balanced styles and the literal-crop target contract passed. The bundle's local extraction/prepare preflight passed with 340/90 pairs, 16/4 identities and no split leakage. The held-out evaluation selector resolves 20 pairs: one index nail per validation identity and all five styles. Reprojecting those 20 approved localized targets through the inverse mapping and unchanged compositor changed zero outside-nail pixels in the full hand; nail-region MAE against approved full-hand target averaged 4.867 RGB levels, due to resampling. The bundle ZIP CRC passed and its embedded scripts match current source bytes.

## Bounded training handoff

The private [Kaggle bundle guide](../guides/nails001-local-v1-kaggle.md) uses the existing pinned FLUX.2 Klein Base revision `a3b4f4849157f664bdbc776fd7453c2783562f4d` and AI Toolkit commit `a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7`. Config: fresh `nails001_local_v1`, edit/reference `control_path`, 512 resolution, rank 16/alpha 16 linear plus rank 8/alpha 8 conv LoRA, BF16, batch 1, accumulation 1, AdamW8bit, learning rate 1e-4, seed 1977. Step **50** is an early checkpoint and stop for held-out visual evaluation; it is only 14.7% of one 340-example pass. Any later stage requires evidence of learning. Config SHA-256: `f0e6116a01ea51e7b319d889050005d59d7fac7824702ed0b3147db2f909d695`.

The pinned trainer is patched only in an isolated Kaggle checkout after an exact source-hash guard. One hook after batch fetch writes step, pair ID, identity ID, finger ID and style ID, so exposure at the checkpoint is known. Base and step-50 adapter inference use identical prompts, seed 1977, 20 steps and guidance 4.0 on 20 held-out fingernails. Full-hand previews use the unchanged nail-only compositor.

At preflight time, local Torch was CPU-only and Kaggle authentication was unavailable to this agent. No localized GPU training or held-out inference had run then. The later step-50 run is reviewed separately, and the experimental adapter stays disconnected from `/nails`.

## First Cell 3 attempt, 2026-09-27

The Supervisor's pasted Kaggle traceback shows the pinned Base download reached 100%, then the launcher failed at `import diffusers` with `ValueError: numpy.dtype size changed, may indicate binary incompatibility`. This occurred before the training subprocess or `train.log` creation. A stale in-process NumPy extension after pip changed dependencies was the likely cause. The corrected runner checks NumPy/Torch/Diffusers imports in a fresh subprocess and can strictly verify/reuse the already patched AI Toolkit checkout. A [same-session recovery cell](../guides/nails001-local-v1-cell3-recovery.md) used the original uploaded bundle without deleting or redownloading it. The corrected future-upload bundle SHA-256 is `73f291b6c580201f6eec8d1f525224638c308e54193c60ee29f26afbd0eb8513`. The subsequent run and evaluation are documented in the linked step-50 report.
