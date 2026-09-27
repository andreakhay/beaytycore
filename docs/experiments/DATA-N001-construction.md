# DATA-N001 real-hand construction, 2026-09-26

**Evidence status: VERIFIED locally for this dataset package.** No NAILS-001 training or real Nails inference occurred.

## Source and terms

The [11K Hands author site](https://sites.google.com/view/11khands) offers the dataset free for reasonable academic fair use and requests citation of Afifi (2019). This capstone source pool uses the author's linked metadata CSV and image archive. Their local SHA-256 hashes are `5f14f117603428c468896c41f85f8fa3dbe6ccfd61021ad3711ce78b71eb9848` and `f15b0d68c2093669aad9d7c9f92f9c184f1020878cdbe2e2482e50348a0f4631`; the ZIP CRC check passed. These terms support the academic pilot, not unrestricted redistribution or commercial deployment. Raw photos and derived training ZIPs remain under ignored `data/nails/` paths.

The CSV contains 11,076 records. Filtering dorsal images with metadata flags `nailPolish=0`, `accessories=0`, and `irregularities=0` produced 3,417 records from 149 distinct identities. A one-photo-per-identity shortlist and eight source contact sheets were visually inspected. Twenty identities were frozen before target rendering, with 16 train and 4 validation. The [source manifest](../data/DATA-N001-source-selection.json) records all 149 candidate identities, source archive member/hash, side, metadata flags, split, selection status, and exclusions. Metadata was not treated as proof: subject `0001022` showed green thumb polish despite `nailPolish=0`. Two masks with visibly partial nail coverage and two sources that failed MediaPipe localization were excluded and replaced from the reviewed reserve pool. The final 20 IDs are in [accepted source IDs](../data/DATA-N001-source-accepted-ids.json).

## Offline segmentation gate

The candidate [mnemic/nails_seg_yolov8](https://huggingface.co/mnemic/nails_seg_yolov8) checkpoint declares CC BY 4.0 and attributes its training data to the Personal Projects Nails Segmentation dataset. The local checkpoint hash is `99b7d1c6ceb4bde32d80fe7ae8c8eb809c27d99b55cf9db54b6692afe68f4070`. It loaded and predicted with `HF_HUB_OFFLINE=1` on CPU in a Nails-only venv with Ultralytics 8.3.244, Torch 2.10.0+cpu, and NumPy 2.4.6. The venv is outside the Hair/Makeup runtime. The [Ultralytics license](https://www.ultralytics.com/license) requires separate review before production distribution; this checkpoint is approved only for this isolated academic dataset pilot.

`scripts/data_n001_segment_review.py` ran at confidence 0.25 and image size 640. All final 20 images produced five detected nail instances. Each Original / Predicted Nail Masks / Overlay sheet was visually reviewed for missing/false nails, skin leakage, cuticle and tip edges, fragmentation, and practical rendering use. Final decisions: **20 ACCEPT, 0 RETRY, 0 REJECT**; see [per-image reviews](../data/DATA-N001-segmentation-review.json). MediaPipe Hand Landmarker and the existing `validate_nail_mask` also passed on all final 20. This is pilot-mask acceptance on these photos, not proof that the checkpoint works on arbitrary user photos.

The local source freeze is `data/nails/work/source-frozen-v4/`; the prediction sheets and masks are `data/nails/work/seg-review-v4/`. Earlier v1–v3 attempts remain in `data/nails/work/` as exclusion evidence. The current production Nails route still uses only a reviewed-mask abstraction and mock response; the YOLO dependency was not wired into the application.

## Deterministic pair construction and review

`scripts/data_n001_selection.py` verifies the frozen source, prediction, and explicit mask-review identities and hashes, then records 21 normalized MediaPipe landmarks for each accepted identity. `scripts/data_n001.py prepare` rendered five styles per identity. The first render pass was visibly flat; its `data/nails/work/DATA-N001-candidates/` output was left unaccepted. The revised renderer retains photographed nail luminance/highlights, softens the cuticle edge inward, and uses landmark direction for French tips and ombre. It changes no pixel outside the original nail mask.

The revised `data/nails/work/DATA-N001-candidates-v2/` has **100 candidates, zero exclusions**. All 20 five-style Original / Nail Mask / Target contact sheets were visually inspected for style, boundaries, leakage, highlights, tip/ombre direction, and scene preservation. Review decisions in `manifests/reviews.json`: **100 ACCEPT, 0 RETRY, 0 REJECT**. These are simple short-nail pilot styles; their small 512-pixel nails limit fine detail. The deterministic targets are suitable for an initial paired-edit training test, but their ability to teach a useful LoRA remains unverified until held-out inference.

Independent pixel QA across all 100 found zero edits outside each binary nail mask, at least 1,576 changed nail pixels per target, 100 unique target hashes, and 20 examples per style. The guarded finalizer rechecked dimensions, masks, captions, hashes, outside-mask equality, duplicate targets, disjoint train/validation subjects, explicit reviews, and ZIP CRC. Final package: `data/nails/work/DATA-N001-final.zip`, SHA-256 `d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb`. Counts: **80 train pairs from 16 identities; 20 validation pairs from 4 identities**; each of five styles has 16 train and 4 validation pairs. The archive contains reference/target/mask files, target instruction captions, pair and review manifests, source/segmentation provenance, and QA report.

## Recorded run commands

These commands were run from the repository root against then-empty output directories. The accepted-ID file and v4 source-candidate manifest contain the manual source review and exclusions; neither is recreated by a metadata filter alone. The pair and segmentation review JSON files also contain manual decisions. Existing output directories deliberately refuse overwrites.

```powershell
python scripts/data_n001_source_select.py shortlist --metadata data/nails/source/11k-hands/HandInfo.csv --archive data/nails/source/11k-hands/Hands-original.zip --output data/nails/work/source-review
python scripts/data_n001_source_select.py review --candidates data/nails/work/source-review/source_candidates_v4.json --accepted-ids docs/data/DATA-N001-source-accepted-ids.json
python scripts/data_n001_source_select.py freeze --candidates data/nails/work/source-review/source_candidates_v4.json --archive data/nails/source/11k-hands/Hands-original.zip --output data/nails/work/source-frozen-v4
$env:HF_HUB_OFFLINE='1'; $env:YOLO_CONFIG_DIR='F:\HAIR\data\nails\work\yolo-config'
& 'data/nails/work/seg-venv/Scripts/python.exe' scripts/data_n001_segment_review.py --source-root data/nails/work/source-frozen-v4 --checkpoint data/nails/checkpoints/mnemic/nails_seg_s_yolov8_v1.pt --output data/nails/work/seg-review-v4
python scripts/data_n001_selection.py --source-root data/nails/work/source-frozen-v4 --segmentation-root data/nails/work/seg-review-v4 --reviews docs/data/DATA-N001-segmentation-review.json --hand-model data/nails/checkpoints/mediapipe/hand_landmarker.task --output data/nails/work/data-n001-input
python scripts/data_n001.py prepare --source-root data/nails/work/data-n001-input --selection data/nails/work/data-n001-input/selection.json --dataset data/nails/work/DATA-N001-candidates-v2
python scripts/data_n001.py finalize --dataset data/nails/work/DATA-N001-candidates-v2 --archive data/nails/work/DATA-N001-final.zip
python scripts/train_n001_bundle.py --dataset data/nails/work/DATA-N001-candidates-v2 --output data/nails/work/NAILS-001-pilot-bundle.zip --steps 75 --save-every 25
```

The bundle is `PREPARED_NOT_TRAINED`, SHA-256 `6c75cec008f5175aeeeaa5e9e611c8de59e7a12d3c5177cbddfa32dd956b1d6c`. It passed the bundle's identity, pair hash, instruction, review, and CRC checks. The 75-step/25-step checkpoint schedule is an initial short probe, not a fixed full-training prescription. The Supervisor's next action is to upload this bundle to an authenticated Kaggle T4 session, pin AI Toolkit to `a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7`, verify the FLUX.2 Klein Base revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, run the bundled `RUN.txt` command, and return checkpoint hashes plus held-out validation contact sheets for evaluation. Stop or continue training based on those results. No NAILS-001 checkpoint currently exists.

## Test isolation and regression

`backend/tests/conftest.py` pins the default Hair test registry and mock engine before collection so a developer `.env` cannot change Hair test expectations. Production Hair settings are untouched. From `F:\HAIR\backend`, `python -m pytest tests -q` passed **78 tests** with one existing `python_multipart` import deprecation warning. A hostile `GENERATION_ENGINE=remote_flux` and optional 13-style registry environment still passed the three affected Hair test modules: **12 tests**.
