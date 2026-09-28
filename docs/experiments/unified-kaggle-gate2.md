# Unified Kaggle Gate 2, persistent foundation and adapter switching

2026-09-28. **Preparation DONE; LOCAL VERIFIED; GPU experiment NOT STARTED, NEEDS VERIFICATION. Gate 2 has not passed.** Supervisor authorized this isolated experiment only. Gate 1 remains passed for its reviewed fixed cases. No final inference API server, application migration or Gate 3 is implemented.

## Authoritative inputs

Use the immutable [Gate 1 reviewed evidence](unified-kaggle-gate1.md) and [resolved versions and measurements](unified-kaggle-gate1-review.json). Application checkpoint: `88acee3be1280f0a98401a93742fabe48bdd4628`; Gate 1 preparation: `8c63afc436571453c01be8f412f05cbd48fd3aca`; review: `ae01f0e559d72ebc2d48a559c550b313f8311b31`. The trusted private Gate 1 bundle SHA is `8ed784714d534ff767dd261bd5d440d643b526cfac60f2d8dccd47e2c9d44293`; returned evidence SHA is `7b427c1421480ef874b1ca3d1fc2e5c29edff0c8419d624973f46ef80b619303`. These source files and the reviewed evidence are not modified.

The same Hair `CrewCut_26_to_original` / `crew_cut`, Makeup `054109` / `natural_makeup`, and Nails `0000045_classic_red__index` / `classic_red` prepared crop are used. Inputs, prompts, adapters and exact returned Gate 1 PNGs are hash verified. No new photos/styles/weights or generation tolerance are introduced. All inference retains Base `black-forest-labs/FLUX.2-klein-base-4B` revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, FP16, CPU offload on GPU 0, 512 square, 20 steps, guidance 4.0, seed 1977.

## Experimental components

| File | Responsibility |
| --- | --- |
| `scripts/unified_gate2.py` | One persistent foundation, exclusive ownership, verified adapter unload/load, unchanged original generation methods, sequence/recovery/concurrency/cancellation probes and evidence |
| `scripts/unified_gate2_bootstrap.py` | Exact observed environment and Base setup, persistent child process, conditional isolated diagnostics after child exit, downloadable success/failure evidence |
| `scripts/unified_gate2_requirements.txt` | Exact observed direct package versions, including Safetensors 0.9.0rc1 |
| `scripts/package_unified_gate2.py` | New private bundle from verified immutable Gate 1 assets, exact Gate 1 outputs and new experiment code |
| `backend/tests/test_unified_gate2.py` | Fake model safety, identity, restoration, concurrency/cancellation and full experiment recording tests |
| `notebooks/unified_gate2_kaggle.ipynb` | Empty output three cell verify/extract, setup/experiment and evidence download workflow |
| `docs/guides/unified-kaggle-gate2.md` | Exact notebook settings, upload and copy/paste cells |

Python 3.12.13, Torch 2.10.0+cu128, CUDA 12.8 and Tesla T4 are checked before installation. Observed direct dependencies and Diffusers Git commit must match Gate 1 exactly in fresh processes. Requirements pin NumPy 1.26.4, Transformers 5.5.3, Accelerate 1.13.0, PEFT 0.18.1, Hub 1.23.0, Safetensors **0.9.0rc1**, Pillow 11.3.0, FastAPI 0.136.1, Uvicorn 0.46.0 and multipart 0.0.26; Diffusers comes from `c943837899b16cbae2f619b8dd4f7bb6f07dd81a`, expected 0.39.0.dev0. Host Torch/companions are constrained. Optional old torchao is removed as in Gate 1; a remaining newer torchao stops reproduction rather than changing behavior. Unrecorded historical transitive versions are not asserted known. Existing global Kaggle package conflicts remain a documented limit, not permission to move CPU vision into this environment.

## Switching and provenance

The persistent worker calls `Flux2KleinPipeline.from_pretrained` once and enables the same CPU offload once. Original feature runtime objects receive that pipeline and Torch without calling their `load` methods. Their existing `generate` methods retain Hair/Makeup padding, Nails crop handling, prompts/settings and output contracts. Hair's runtime view already identifies TRAIN-001, so its internal activation method returns without an additional load; the experimental owner verifies Hair's actual adapter first.

One `asyncio.Lock` covers the complete switch and generation operation. GPU work runs in a thread while ownership is held. Before a transition, CUDA is synchronized. The prior state is marked uncertain, ordinary `unload_lora_weights()` runs, and both library adapter inventory and residual LoRA tensor names must be empty. The requested file/hash and original feature artifact verifier are checked; `load_lora_weights(directory, weight_name=...)` uses the same ordinary unnamed single adapter mechanism as the original load methods. No fusion, stacking, hot swap or cached collection of active LoRAs is used.

The pinned library's `get_list_adapters()` and `get_active_adapters()` must identify exactly one transformer adapter. Every LoRA layer must independently have that sole active adapter, with no disabled or merged layer. Its actual named LoRA tensors must match the requested artifact after the pinned library's own `lora_state_dict` conversion, with exact tensor equality. Converted tensor hash/count, verified layer count and the library adapter name are recorded. Verification runs before inference and after completion. Wrong or unknown state marks the runtime unready and blocks generation. Pipeline/transformer/text encoder/VAE/scheduler/tokenizer object identities must remain unchanged. Inference metadata is validated against requested feature/style, adapter ID/hash, Base revision and settings; the wrapper additionally records requested and active feature identities.

API behavior was checked against the [pinned Diffusers loader source](https://github.com/huggingface/diffusers/blob/c943837899b16cbae2f619b8dd4f7bb6f07dd81a/src/diffusers/loaders/lora_base.py) and [Flux2 loader conversion](https://github.com/huggingface/diffusers/blob/c943837899b16cbae2f619b8dd4f7bb6f07dd81a/src/diffusers/loaders/lora_pipeline.py). This source inspection supports harness design, not a claim that real cross feature switching has succeeded.

## Sequence, equivalence and measurements

Primary sequence: **Hair → Makeup → Nails → Hair → Makeup**. One extra **Nails → Hair → Makeup** cycle supplies comparable later memory observations without a large benchmark. Each output records PNG SHA, RGB equality/changed pixels/mean and maximum channel difference against its exact Gate 1 output and first shared output. No acceptance tolerance or automatic quality approval exists.

If any RGB difference occurs, bootstrap waits for the persistent process to exit before running two fresh isolated diagnostic processes for each affected feature using the original Gate 1 worker. They use new Gate 2 output directories. Isolated repeats are compared with each other, Gate 1 and every corresponding shared output. Evidence is preserved for attribution review; the harness does not conclude that switching caused differences. This is conditional diagnostic work, not a rerun of Gate 1. No diagnostic Base coexists with the persistent Base.

One second samples preserve Linux process RSS/high water, available system RAM, PyTorch allocated/reserved/peaks and whole device usage. Events include synchronized transition durations, inference durations and request boundary measurements. Same feature post inference observations are grouped for memory growth review. Nails gets an optional peak reset for measurement only, under the reused telemetry guard. No `empty_cache` loop is used to disguise caching/growth. Optional telemetry failures are retained as warnings/null, not measured zero; no invented leak threshold or guaranteed peak bound is assigned. Whole device sampled peaks are distinct from PyTorch peaks.

## Controlled failures and ownership

After normal switching, five switch failures are injected: missing scratch path, invalid harmless scratch text, exception after unload, exception after load, and simulated OOM before load. Real adapters are never altered, converted or exhausted. Each failure must block inference, clear uncertain partial state and restore the previous artifact through unload/load and actual tensor verification. Restoration failure marks `ready=False`, clears active identity and fails closed. Each successful restoration is followed by valid original inference. Real CUDA OOM recovery remains unverified.

Two competing feature tasks execute real inference inside the same experimental owner. A controlled completion latch makes overlap deterministic even with fast local fakes; the waiting feature cannot switch until the first operation finishes. The cancellation probe cancels the first caller twice while its thread works. Shielded waits continue draining that thread, including exceptions, before ownership is released. Pending GPU work is synchronized on the error path too; a synchronization failure is recorded and the runtime remains unready so later requests cannot compute. Its completed output/provenance is still preserved. These are async runtime probes, not real HTTP disconnect tests, since no server exists. Local tests also cover failed restoration, cancelled inference/error drain and failed CUDA synchronization paths.

There are 17 original inference outputs on the normal path: eight sequence/cycle cases, five restoration cases and four competing/cancellation cases. No Nails localization, segmentation, refinement, reconstruction, compositing or deterministic renderer runs in Kaggle. Existing application, GPU servers, requirements/configuration, legacy routes and Gate 1 artifacts remain untouched.

## Local validation evidence

Preparation checks on system Python 3.11, not the candidate GPU environment:

* New Gate 2 focused suite: **40 passed**. Full sequence with one fake foundation, restored output/provenance, wrong loaded/response identities, changed foundation, residual tensors, missing/invalid/partial/OOM injections, failed restoration/unready behavior, serialization, repeated cancellation and draining failed threads, exact environment mismatch, actual inspector tensor comparison, failed bootstrap evidence and conditional isolated diagnostics covered.
* Gate 1 plus Gate 2 harness suites: **79 passed**, one existing python_multipart deprecation warning. No unrelated application suite rerun.
* New Python files parse. Notebook JSON, cell IDs, all three code cells, empty outputs/counts validated. Optional nbformat schema validator is not installed locally.
* Notebook Cell 1 executed against a simulated local Kaggle layout: outer SHA, 39 member CRC/inventory, individual hashes, safe extraction passed. Extracted `scripts/unified_gate2.py --verify-only` returned **GATE_2_ARTIFACT_PREFLIGHT_OK (no model load)** with original adapter verifiers and reviewed fixed outputs.
* Final bundle runtime/contract/Gate 1 bytes match the repository and immutable source. No Torch foundation, candidate package installation or GPU inference ran locally. Local fakes are not evidence of persistent GPU compatibility.

Final private handoff: `artifacts/unified_gate2_20260928_v5.bin`, **128,940,681 bytes**, SHA-256 `0e5ffd854f394f86e5c1ca49d47b9b230b0088aae2da828d893601330d190feb`, 39 members. Adapters occur once each in the new bundle. It is ignored by Git. Earlier local bundles are drafts; only `_v5.bin` is the handoff. New notebook paths `/kaggle/working/gate2_bundle`, `/kaggle/working/unified_gate2` and `/tmp/gate2-hf-cache` are separate from Gate 1/production roots and refuse overwrite. Rebuild to a new filename only, then independently update/verify handoff hashes before use.

## Kaggle evidence required

Use the [exact handoff](../guides/unified-kaggle-gate2.md). Return `evidence.zip`, all Cell 3 output and the actual accelerator setting, including failed runs. Successful completion is **SWITCHING_COMPLETED_REVIEW_REQUIRED**, never automatic Gate 2 acceptance. A differing shared result reports **SWITCHING_COMPLETED_ISOLATED_REPEATS_REQUIRED** and includes conditional diagnostic evidence. Review one persistent foundation, adapter identity, all equivalence/restoration outcomes, serialization/cancellation, timing and memory stability before considering the twelve Supervisor pass criteria. Real switching, hook behavior and long lived RAM/VRAM are **NEEDS VERIFICATION**.

Current preparation status: **GATE_2_READY_FOR_KAGGLE**. The next milestone is the manual Gate 2 run and independent returned evidence review. Gate 3, final shared server and centralized live application validation remain unperformed.
