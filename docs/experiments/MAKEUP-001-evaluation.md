# MAKEUP-001 held-out evaluation

Status: VERIFIED technical artifacts; Project Lead approved practical visual quality for app integration; generalization EXPERIMENTAL. Recorded 2026-09-26.

## Evidence

The downloaded `C:/Users/Gigabyte/Downloads/makeup001_250_with_evaluation.zip` passed CRC, checkpoint and optimizer hashes, and all 40 evaluation output hashes. Training completed at step 250 with finite recorded losses. Final adapter SHA256: `f6f0419e4259a75102f08a450222ad806e3aec1c2ae50ff89f875139084ae510`.

The two held-out identities are `054109` and `056266`. Each has ten Base outputs and ten MAKEUP-001 outputs using the fixed application prompt presets. Sheet columns are Original, Base, MAKEUP-001. The Project Lead supplied both comparison sheets and stated: "I reviewed the images and the one on the right is consistently good". This records practical approval of the adapter's displayed outputs, not a quantitative identity metric or independent full-resolution review of every output.

## Visible observations

MAKEUP-001 produces more coherent cosmetic regions than Base in these sheets, particularly for Smoky Glam and Rosy Pink. Base shows broad eye or cheek pigment and exaggerated brows in several rows. The adapter's red and dark lip presets, pink preset, warm bronze eyes and smoky eyes are visually responsive to instructions. Broad hairstyle and background layout remain recognizable.

The adapter also visibly retouches both faces. Complexion, skin texture, apparent skin tone, eyebrows, eye contours and mouth details differ from the originals. This is not evidence of unchanged facial geometry or a proved identity-preservation improvement over Base. Natural Makeup and No-Makeup Makeup appear substantially more glamorous than their names imply; Natural, Soft Glam and Matte Nude have limited separation in these small sheet views. Hair tone and facial lighting can change. These limitations should remain documented rather than hidden by the quality approval.

## Decision and next action

The Project Lead's practical approval permits the previously authorized isolated Makeup app integration to proceed. Keep all ten inference presets and the current checkpoint; no retraining or new dataset experiment is required by this review. Do not describe MAKEUP-001 as ten trained FFHQ classes or as guaranteed identity preserving. Validate the real Makeup request and result path separately while leaving Hair untouched. Unseen-user generalization, exact geometry preservation and subtle-style fidelity remain unverified.

The isolated app implementation and inference bundle are now locally verified. The first actual Kaggle model load and live browser generation remain pending. See [integration evidence](MAKEUP-001-integration.md) and [the next notebook cells](../guides/makeup001-live-demo.md).
