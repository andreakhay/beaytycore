# Unified Kaggle Gate 1, common environment and individual equivalence

2026-09-28. **Preparation DONE, LOCAL VERIFIED. Live experiment NOT STARTED, NEEDS VERIFICATION. Gate 1 has not passed.** Supervisor authorized only this experiment, not a unified server, application migration or Gate 2. Application checkpoint: `88acee3be1280f0a98401a93742fabe48bdd4628`.

## Design and implementation

One candidate dependency environment, three sequential fresh Python subprocesses. Each imports its existing feature runtime class, verifies immutable artifacts, loads a fresh pinned Base plus that feature's adapter, and calls its original `generate` method once. Process exit disposes CPU weights, GPU context and offload hooks before the next feature. No simultaneous foundations, cross feature switching, API server, tunnel, training or backend/frontend change.

| File | Responsibility |
| --- | --- |
| `scripts/unified_gate1.py` | Bundle/contract preflight, environment verification, sequential worker orchestration, existing runtime calls, timing, optional memory telemetry, output/provenance validation and reference comparison |
| `scripts/unified_gate1_bootstrap.py` | New Kaggle environment only: preserve host Torch/companions, install candidate, check fresh imports, download one snapshot/cache, run workers and package success/failure evidence |
| `scripts/unified_gate1_requirements.txt` | Separate candidate requirements; originals untouched |
| `scripts/package_unified_gate1.py` | Verify original artifacts/reference records and make a new private bundle with distinct feature paths |
| `notebooks/unified_gate1_kaggle.ipynb` | Empty-output, three-cell launch notebook with exact upload SHA, safe extraction, bootstrap and evidence download |
| `backend/tests/test_unified_gate1.py` | Focused harness tests with fake subprocess/GPU boundaries |

Candidate matches Nails inference requirements: NumPy 1.26.4, Diffusers commit `c943837899b16cbae2f619b8dd4f7bb6f07dd81a` (0.39.0.dev0), Transformers 5.5.3, Accelerate 1.13.0, PEFT 0.18.1, Hub 1.23.0. Safetensors/server/Pillow retain original ranges and their resolved versions are recorded. Installation constrains existing Kaggle Torch, torchvision and torchaudio. It reuses the Hair/Makeup bootstrap safeguard to remove optional torchao below 0.16 in this new notebook only. This is not quantization or a change to any original requirement file.

All cases retain `black-forest-labs/FLUX.2-klein-base-4B` revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, FP16, model CPU offload on GPU 0, 512 square, 20 steps, guidance 4.0 and seed 1977. The original prompts, adapter calls, padding/crop handling and result generator/provenance are reused. Only the experiment guards optional Hair CUDA statistic calls and wraps Base/adapter calls for timing. No model behavior is patched. Unavailable telemetry is reported as unavailable/null, not a real zero measurement.

## Fixed cases and references

| Feature | Input / style | Reference and limits |
| --- | --- | --- |
| Hairstyle | Accepted held-out DATA-001 `CrewCut_26_to_original`, generated 512 portrait; `crew_cut` | TRAIN-001 step-250 adapter evaluation on that exact input, same prompt/settings. Not a fresh current server capture. Evaluation runtime omits exact Diffusers/Transformers/Accelerate/PEFT versions. |
| Makeup | Reviewed public FFHQ-Makeup bare portrait `054109`, 512 JPEG; `natural_makeup` | Reviewed MAKEUP-001 step-250 held-out adapter output, identical source hash/prompt/settings. Original photo credits and academic dataset terms retained. Not corrected V2 serving evidence; full evaluation dependency versions missing. |
| Nails | Frozen DATA-N001-LOCAL-v1 held-out `0000045_classic_red__index`, prepared 512 crop; `classic_red` | Verified step-50 localized adapter evaluation. Crop transform/input hash retained; no localization, segmentation or compositing moves to GPU. Other Nails styles/full hand pipeline are outside this gate. |

| Feature | Input SHA-256 | Historical output SHA-256 |
| --- | --- | --- |
| Hair | `3690f83b3f517ea1d2408ee35c1cdb3bdb89ddc3a69d061d6b57fba51f69e537` | `da234556a871228b97543f97b3a9fe650894b24703510fff2836a12eb66c3497` |
| Makeup | `81e57faca39e3989ed9920ebd6568efad563ae4f012f3fbb130918858d18e8ed` | `2c8a1511035fec5b326878af85130cdb10118c3706a56eae168241f395f8fd39` |
| Nails | `7e28a5bc644b2970298fb04f53b95008a4eee47816e379368ae748b828626cf4` | `c9101d97bed8d48990988cba2bc63aa4bd733eff101a7ff9c7813a37fe2d037b` |

The private plan contains checkpoint identity/hash, exact prompt, settings, source archive hashes and selected reference records. Each input/reference is verified before inference. Candidate PNGs, full response envelopes, file hashes, RGB equality, changed pixels and channel differences are preserved. No acceptance tolerance or automatic quality judgment exists. Historical output differences cannot conclusively be attributed to the candidate versions without a current-stack comparison.

## Telemetry and failure policy

- Record Python, Torch/CUDA/GPU, Diffusers Git origin and all requested dependency versions; reject mismatched direct candidate pins or changed Torch.
- Record scratch before setup, cache/snapshot unique backing bytes, extracted bundle size, setup/download/loading/adapter/inference timings.
- Linux `/proc` RSS and high-water mark, system available/total RAM; PyTorch allocated/reserved and both peaks; `nvidia-smi` whole-device used/total memory. During model operations sample approximately once per second. Device sampled maximum is not an exact continuous peak. PyTorch peaks do not equal whole-device usage; a failed reset is explicitly recorded.
- Optional telemetry failures do not stop inference. The original Hair optional-stat failure is guarded only in the experiment and restored afterward.
- A worker failure records dependency/import, adapter validation/loading, Base loading, preprocessing, inference, CUDA/resource, output/provenance or harness boundary and sanitized exception/traceback. No retries or model changes. A 30-minute worker deadline kills/waits that process before the next feature; partial progress is preserved when available.
- Global candidate setup/import failures stop GPU work and preserve setup evidence. Missing/corrupt bundle preflight never starts inference. A feature failure never becomes Gate 1 success; later features can still be tested in fresh processes.
- No remote auth is needed. Ephemeral process-only keys satisfy the reused runtimes' load checks; no listener starts and no key is written. Optional HF access remains Kaggle Secrets only.

## Local evidence

- `python -m pytest backend/tests/test_unified_gate1.py -q`: **39 passed**, one existing python_multipart deprecation warning. Includes three original generation methods with fake GPU/artifact boundaries, exact settings/provenance, load/adapter/inference failures, version/commit checks, sequential feature isolation, timeouts, optional telemetry, path/hash safety, secret redaction and early failure evidence. These are not GPU inference results.
- All new Python and embedded runtime files parse. Notebook JSON structure and all three cell syntax checks passed; the optional nbformat schema validator is not installed locally. The notebook includes cell IDs, empty outputs and execution counts, and standard nbformat 4.5 metadata.
- Executed notebook Cell 1 against a simulated local Kaggle input/working layout. Outer SHA, CRC, exact member inventory, safe extraction and embedded syntax passed.
- Ran extracted final bundle `scripts/unified_gate1.py --verify-only`: **GATE_1_ARTIFACT_PREFLIGHT_OK**, all original adapter verifiers and approved case/settings checks passed. No Torch/Diffusers foundation or GPU inference was loaded.
- Current Hair/Makeup/Nails server bytes match those copied into the final experiment bundle. Git changes contain no original runtime/application edits.
- No candidate GPU packages were installed locally. The backend venv lacks pytest; the already installed system Python 3.11/pytest ran the focused suite. No full application suite rerun because application code is untouched.

Final private upload: `artifacts/unified_gate1_20260928_v2.bin`, **128,203,008 bytes**, SHA-256 `8ed784714d534ff767dd261bd5d440d643b526cfac60f2d8dccd47e2c9d44293`, 30 members. It is ignored by Git. Earlier local draft bundles are not the handoff. Do not commit adapters, images, Base cache or downloaded evidence.

Rebuild without overwriting the handoff:

```powershell
python scripts/package_unified_gate1.py --output artifacts/unified_gate1_rebuild.bin
```

Defaults name the inspected local artifact locations; override CLI input paths on another machine. A rebuilt outer hash must be independently verified and updated in the notebook/guide before uploading. No secret belongs in that process.

## Kaggle evidence still required

Use the [exact handoff](../guides/unified-kaggle-gate1.md). Return `evidence.zip`, Cell 3 status and actual accelerator selection, including failed/partial runs. Review environment/commit pins, all three valid outputs/provenance, historical differences, RAM/VRAM/storage/time and any failures before deciding Gate 1 acceptance. Completed inference is labeled `INDIVIDUAL_INFERENCE_COMPLETED_REVIEW_REQUIRED`, never an automatic pass.

Current result: **GATE_1_READY_FOR_KAGGLE**. Actual inference, candidate output equivalence and GPU/CPU resource feasibility remain NEEDS VERIFICATION. Separate services and legacy routes remain unchanged. Gate 2, final unified runtime and centralized live application acceptance have not begun.
