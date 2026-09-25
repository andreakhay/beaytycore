# TRAIN-002: Supervisor 500-step artifact verification

Status: **training complete; artifact verified locally; model quality and multi-adapter runtime unverified**. The Supervisor ran the pinned AI Toolkit job on Kaggle T4 and supplied `D:/Downloads/train002_500_artifacts.zip`. Codex did not run the GPU job.

## Archive and provenance

- Archive: 169,509,902 bytes; SHA-256 `2093b33be829930d39555d584ff5c0571ed02daf9eae13b0af0c4eb32dcea25e`; 19 ZIP members; all member CRC checks passed.
- Frozen DATA-002 manifest: `25a3200c9a79be85ce19f690ba81f564d57d55d86d36e6383b0cacd1188ec5ab`.
- Training dataset: 100 train and 20 validation identities; 200 train and 40 validation directional pairs; ten balanced target styles. Review mode `automated_unreviewed`; visual QA was not performed.
- Base: `black-forest-labs/FLUX.2-klein-base-4B` at `a3b4f4849157f664bdbc776fd7453c2783562f4d`. AI Toolkit commit `a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7`. Runtime reported Python 3.12.13, PyTorch 2.10.0+cu128, CUDA 12.8, Tesla T4.

## Training result

`training_summary.json` reports `success: true`, exit code 0, highest loss step 500, no stop reason, and a final checkpoint/optimizer save after the last step. The 996 captured loss records include duplicate progress observations across 501 unique steps numbered 0–500; every recorded loss is finite. The run reported 17,848.35 seconds including load, 31.53 seconds per recent step, and 13,531 MiB peak GPU use.

The archive contains the 250-step and 500-step `.safetensors` checkpoints and a 47,115,659-byte `optimizer.pt`. The final adapter is 46,223,600 bytes with SHA-256 `59d527217a68139bc2aaa4eedbfcd2d5789ef115f8ecb924410eea24a952939b`. This hash matches `adapter/metadata.json`, and the packaged adapter is byte-identical to the final checkpoint. Safetensors headers identify steps 250 and 500 respectively. The training config hash matches adapter metadata. Metadata status is `UNVALIDATED_FOR_RUNTIME`.

## Remaining gates

This verifies the training run and artifact lineage, not hairstyle quality. DATA-002 counterparts were accepted structurally without human visual review. Ten held-out Base-versus-adapter comparisons were subsequently generated and reviewed preliminarily; see [TRAIN-002 evaluation](TRAIN-002-evaluation.md). Actual T4 adapter switching and activation of TRAIN-002 styles have not occurred. TRAIN-001 remains the live fallback.
