# DATA-N001 Nails edit pilot

**Status: DONE for the reviewed 100-pair academic pilot; NAILS-001 step 25 was trained experimentally and failed the five-style held-out quality gate.** The complete construction and verification record is [DATA-N001 construction](../experiments/DATA-N001-construction.md), followed by the [step-25 diagnostic](../experiments/NAILS-001-step025-diagnostic.md).

The source is the [11K Hands author dataset](https://sites.google.com/view/11khands), offered free for reasonable academic fair use with requested Afifi (2019) citation. The local source-selection manifest records 149 inspected metadata-eligible identities, 20 final selected identities, exact source members/hashes, hand side, dorsal flag, polish/accessory/irregularity metadata, fixed 16/4 identity split, and exclusion reasons. One metadata false negative for nail polish was removed. Source photos and the final training ZIP remain in ignored local `data/nails/` paths.

The isolated `mnemic/nails_seg_yolov8` CPU checkpoint produced five masks on each selected hand. Original / Predicted Nail Masks / Overlay sheets were visually reviewed: **20 ACCEPT, 0 RETRY, 0 REJECT** for this pilot only. The existing MediaPipe Hand Landmarker and nail-mask geometry check passed on all 20. [Per-image segmentation decisions](DATA-N001-segmentation-review.json) and the [source selection manifest](DATA-N001-source-selection.json) are retained. Segmentation training data and this generative edit dataset remain separate.

The deterministic renderer used the reviewed masks and landmarks to make Classic Red, Nude Pink, Glossy Black, French Tip and Pink Ombre targets. The first flat-looking pass was not accepted. The revised 100 candidate Original / Nail Mask / Target sheets were visually reviewed: **100 ACCEPT, 0 RETRY, 0 REJECT**. The final package has 80 train pairs from 16 subjects and 20 held-out validation pairs from 4 subjects, balanced at 16/4 per style. Pixel QA found no edits outside the original nail masks. The finalizer verified hashes, mask/image dimensions, target changes, captions, identity separation, duplicates, review decisions and ZIP CRC.

Local artifacts:

- Final archive: `data/nails/work/DATA-N001-final.zip`, SHA-256 `d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb`.
- Reviewable candidate directory: `data/nails/work/DATA-N001-candidates-v2/`, with all 100 Original / Mask / Target sheets and explicit pair reviews.
- Reviewed segmentation: `data/nails/work/seg-review-v4/`, with 20 Original / Predicted Masks / Overlay sheets.
- Frozen 20-photo source: `data/nails/work/source-frozen-v4/`.
- Prepared, untrained Kaggle bundle: `data/nails/work/NAILS-001-pilot-bundle.zip`, SHA-256 `6c75cec008f5175aeeeaa5e9e611c8de59e7a12d3c5177cbddfa32dd956b1d6c`.

The prepared training bundle above was used for the completed step-25 experiment. Its held-out results did not prove useful five-style behavior. The later inference-only train-set probe is complete in the [step-25 diagnostic](../experiments/NAILS-001-step025-diagnostic.md). A separate localized derivative of these same approved pairs and frozen identities produced a verified [step-50 checkpoint](../experiments/NAILS-001-LOCAL-v1-step050-evaluation.md). Five-style model quality still failed. The Supervisor then froze training and selected a [hybrid Nails route](../experiments/NAILS-001-hybrid-integration.md): the custom adapter for Red and Black, and the shared deterministic renderer for Nude, French and Ombre. The approved DATA-N001 archive remains byte identical; live GPU app inference still needs verification.
