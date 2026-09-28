# 0001. Shared application architecture

**Date**: 2026-09-27  
**Status**: DEPRECATED as a phase 1 routing plan by the Supervisor's 2026-09-27 integration direction; shared GPU runtime remains PROPOSED for later evaluation

**Current implementation**: Phases 1 and 2 established registry dispatch and central frontend calls. Phase 3 locally/mocked validated those paths and hardened malformed-response boundaries. The Supervisor subsequently authorized the feasibility audit below, without implementation or live GPU execution. GPU consolidation remains PROPOSED and live centralized inference remains unverified. See [Phase 3 evidence](../experiments/central-architecture-phase3.md) and [state](../../context/state.md).

**2026-09-28 experiment update:** the separately authorized Gate 1 completed on Kaggle and passed evidence review: three individual fixed cases under one candidate environment, exact historical-reference PNG/RGB equality, unchanged settings and no observed resource blocker. Pip conflicts in unused preinstalled libraries remain documented. Each case used a fresh sequential pipeline, not one shared foundation. The proposal/audit below remains historical; Gate 2/shared server and live centralized application acceptance are still unverified and unimplemented. See [Gate 1 reviewed evidence](../experiments/unified-kaggle-gate1.md) and [reproduction handoff](../guides/unified-kaggle-gate1.md).

## Summary

Use the existing Next.js app and FastAPI application as the one public system. FastAPI owns upload checks, feature selection, result formatting, and the Nails CPU pipeline. The three trained LoRAs are candidates to share one loaded FLUX.2 Klein Base in one GPU process, with one adapter active at a time. Keep the current independent GPU services until a bounded dependency, switch, resource and output test proves that consolidation preserves their behavior.

## What exists

| Concern | Inspected implementation | Evidence limit |
| --- | --- | --- |
| Web app | One Next.js app with Hairstyle `/`, Makeup `/makeup`, Nails `/nails`; all use `frontend/lib/api.ts` and the same FastAPI base URL | Local flows are tested; no hosted deployment |
| Central API | One `backend/app/main.py` serves `/generate`, `/makeup/generate`, `/nails/generate`, catalogs and health | Shared JPEG/PNG, size, dimension, EXIF and RGB validation; shared `GenerateResponse` data URL shape |
| Hairstyle | `GenerationEngine` selects mock or `RemoteFluxEngine`; remote GPU service loads Base plus TRAIN-001, with optional TRAIN-002 adapter switch | TRAIN-001 browser request reported; preservation inadequate; TRAIN-002 public test reported, limited visual evidence |
| Makeup | `RemoteMakeupEngine` calls a separate GPU service with one pinned MAKEUP-001 adapter and ten prompt presets | Local contract and UI pass; corrected GPU browser result still needs verification in current records |
| Nails | `HybridNailsPipeline` locates hands, segments plates, then uses remote NAILS-001 step 50 for Red/Black or local deterministic renderer for Nude/French/Ombre; final compositing checks pixels outside masks | Hand A live results and local geometry pass; Hand B and full quality gate remain open |
| GPU | Three scripts each load FLUX.2 Klein Base in their own service and protect inference with a lock | Sharing Base across Hair, Makeup and Nails in one process has not been tested |

The phrase “working” means the routes and selected paths function at their recorded evidence level. It does not imply that every live model path or visual quality gate is complete.

## Decision proposed

### Application boundary

```text
Browser (one Next.js app)
  -> one FastAPI application API
       -> Hairstyle engine -> GPU client
       -> Makeup engine    -> GPU client
       -> Nails pipeline   -> CPU localization, segmentation, renderer, compositor
                              -> GPU client for Red and Black crops only
  -> one result contract -> browser preview or download
```

Phases 1 and 2 implemented `/features`, `/features/{feature_id}/styles` and `/features/{feature_id}/generate` through the existing feature handlers and shared frontend client. Legacy routes remain compatible. The browser sends multipart `image` and `style_id` and receives `GenerateResponse`; GPU credentials and adapter paths stay in the backend. The unified GPU proposal below does not require another application router or UI migration.

The central API chooses the engine from server configuration and the feature route. It validates the image and style, normalizes only as the selected feature requires, invokes the feature pipeline, then returns status, image, dimensions, generator and trustworthy metadata. Unsupported styles stop before inference. Remote errors remain errors and never silently become mock output. Feature health must distinguish API availability, configuration and actual GPU readiness; `/health` currently describes only the API and Hairstyle engine.

### GPU boundary

**Current deployable shape:** one local or hosted FastAPI application plus independent private GPU services. Only start the GPU sessions needed for a demo. This preserves the already tested feature paths and keeps adapter switching isolated.

**Consolidation target, subject to experiment:** one private GPU worker process holds one pinned FLUX.2 Klein Base pipeline and one active LoRA. A registry maps `(feature, style_id)` to an approved adapter ID, pinned hash, prompt, steps, guidance and seed. The worker verifies all artifact hashes at startup, changes adapters only while holding one process wide inference lock, runs the selected edit and returns the actual active adapter metadata. It must clear or restore the prior adapter after a failed switch and mark itself unready if restoration fails. No concurrent request may observe another feature's adapter. Nail Red/Black sends each localized 512 pixel crop and the worker returns a raw crop; the central API keeps localization, deterministic styles and final mask compositing. The worker does not accept arbitrary prompts or adapter IDs from the browser.

Hair's TRAIN-001/TRAIN-002 switch is an existing precedent, but it does not establish safe Hair/Makeup/Nails switching. First compare each feature's separate service with the shared worker on fixed inputs and settings, including Hair -> Makeup -> Nails -> Hair, hashes, response metadata, output visuals, memory, latency and recovery after a forced switch failure. Cut over one feature at a time by changing only its server side GPU client URL. Keep the separate services and configuration as rollback until all three comparisons pass. A single T4 still runs one inference at a time; consolidation saves duplicate Base loads when features share one live session, but does not increase throughput. Nails may still require five sequential crop edits per hand.

## Data flow and file handling

1. The browser previews the chosen local image and posts the original file to FastAPI. Keep current 8 MB, JPEG/PNG, dimensions and decoded pixel limits. Do not log image bytes or data URLs.
2. FastAPI validates once, corrects EXIF orientation and converts to RGB. Hairstyle and Makeup prepare their own 512 by 512 aspect padded portrait. Nails keeps the original image for final output, creates its 512 by 512 hand view, localizes and segments nails, and sends only approved model crops to GPU.
3. The private GPU service receives image bytes over authenticated HTTPS, applies the pinned prompt and adapter, and returns PNG bytes plus model provenance. FastAPI checks content type, byte size, dimensions, status and expected model metadata before accepting remote output. Current Hair validation should be brought to the same provenance standard as Makeup and Nails when the worker is consolidated.
4. FastAPI completes feature specific processing. Nails composites onto the original image with the plate mask and verifies unchanged pixels outside the mask. It returns the current inline base64 data URL. The browser displays it and can download locally.

For the current demo, keep results in memory for the request and do not add a database, object store or permanent portrait archive. This matches the actual API and avoids handling retained personal images. The existing training datasets and private adapter bundles are offline artifacts, not user upload storage. If a hosted service later needs durable results, accounts, or requests surviving disconnects, design retention and access rules first, then add private object storage and a small job store. Do not add Redis, a broker, Kubernetes or microservices for the present single GPU demo.

## Technology and service structure

| Layer | Choice | Reason |
| --- | --- | --- |
| Web | Existing Next.js, TypeScript and Tailwind | Already implements all three pages and one API client |
| Application API | Existing Python FastAPI, Pydantic, Pillow and HTTPX | Already validates uploads, routes features and formats results |
| CPU vision | Existing MediaPipe plus isolated YOLO segmenter interpreter and deterministic renderer | Nails geometry and dependency isolation are feature specific |
| GPU inference | Existing pinned Torch, Diffusers `Flux2KleinPipeline`, Base snapshot and verified LoRA files | One Base can be reused only after cross feature switch verification |
| Transport | Browser to FastAPI over HTTPS; FastAPI to GPU over authenticated HTTPS | Fits the existing multipart contract and temporary Kaggle tunnel |
| Persistence | None for user requests in current demo | No current product requirement for saved history |

Suggested code organization after the bounded consolidation, using moves only where they remove real duplication:

```text
frontend/app/{page.tsx,makeup/page.tsx,nails/page.tsx}
frontend/lib/api.ts
backend/app/main.py                 public routes and shared request/response contract
backend/app/generation/             Hairstyle and Makeup engine adapters
backend/app/nails/                  Nails CPU pipeline and GPU crop client
backend/app/styles.py, makeup_styles.py, nails/styles.py
backend/app/inference_client.py     shared authenticated HTTP transport and image checks, if extracted
scripts/gpu_inference_server.py     proposed one Base plus adapter registry runtime
scripts/*bootstrap.py              existing separate GPU launchers kept during migration
```

The proposed `inference_client.py` centralizes only common HTTP, authentication, timeout, error and image verification mechanics. Prompts, style catalogs, adapter contracts, preprocessing, Nails masks and result semantics stay feature specific. A feature registry entry should be declarative and immutable for a deployment; adding a future FLUX edit feature means a catalog, adapter contract, optional preprocessing/postprocessing module, central route and evaluated registry entry. A non FLUX feature can use a different engine behind the same public response contract without forcing it into the FLUX worker.

## Inference and failure policy

- Load the Base once when each GPU session starts. Verify pinned Base revision and adapter hashes before reporting ready. Keep one adapter active at a time on a T4 unless measured memory evidence supports more.
- Allow one GPU inference at a time in each process. Return a clear busy response, or a small bounded wait managed by the application API. Do not create an unbounded in memory queue. Use a request ID and log feature, style, adapter ID, elapsed time, error class and readiness, without portraits or prompt contents.
- Preserve the current synchronous request contract for the local demo while measured completion fits the configured HTTP limits. Nails Red/Black currently takes about 379 to 382 seconds for a five nail Hand A request, whereas its current GPU client timeout is 300 seconds per crop; a hosted proxy may have a shorter whole request limit. A deployment must measure end to end request time and either set an actually supported timeout or introduce a job API before relying on that route. An async job API is a later capacity and hosting decision, not an assumed current component.
- A GPU session or tunnel ending makes only its model paths unavailable. Nails deterministic styles can continue locally. Report readiness per feature, and never label a mock image as a trained result.

## Options and rationale

1. **Keep three unrelated public backends:** duplicates upload, result and deployment logic and contradicts the already central FastAPI implementation.
2. **Central FastAPI with three private GPU services:** lowest migration risk and deployable now, but each simultaneous service loads its own Base.
3. **Central FastAPI with one shared FLUX worker:** simplest long term GPU footprint for this common Base, but cross feature adapter switching and output equivalence need a controlled test. This is the proposed target after option 2 remains operational.
4. **Queue, database and multiple workers now:** could support durable jobs and throughput later, but introduces state and operating cost before demand or hosting evidence justifies it.

## Migration and verification

1. Document the existing API and per feature readiness without changing model behavior. Add a shared remote transport only if its tests preserve the current contracts.
2. Build the shared GPU worker beside the three current servers. Validate startup hashes, one active adapter, sequence switching, concurrency, failure restoration, result dimensions and provenance. Compare reference outputs and memory/latency on the actual GPU.
3. Route one feature at a time through the worker using server side configuration. Run browser and API regressions, inspect images, then retain or roll back that feature independently. Do not remove the old runtime until all feature gates pass.
4. Decide a durable job/storage design only when a chosen host or measured long request behavior requires it. Decide production hosting separately; Kaggle and Quick Tunnel are verified demo mechanisms, not persistent availability guarantees.

This proposal does not change confirmed model, dataset, hybrid Nails, or frontend decisions. The one shared GPU worker is a major deployment architecture change and requires Supervisor approval before implementation or replacing the separate services.

## References

Inspected source: `backend/app/main.py`, `backend/app/generation/`, `backend/app/nails/`, `frontend/lib/api.ts`, `frontend/app/`, `scripts/kaggle_inference_server.py`, `scripts/makeup_inference_server.py`, `scripts/nails001_local_inference_server.py`. Evidence and approvals: `context/state.md`, `context/architecture.md`, `context/decisions.md`, `docs/experiments/MAKEUP-001-integration.md`, `docs/experiments/NAILS-001-hybrid-live-handoff.md`.

## Unified Kaggle feasibility audit, 2026-09-27

**Result: UNIFIED_KAGGLE_RUNTIME_CONDITIONALLY_FEASIBLE.** Source and artifact compatibility are promising. One common Python stack, cross feature adapter switching, output preservation, RAM and recovery have not been measured on Kaggle. No notebook, runtime, client, package environment, model or generation setting was changed in this audit. No GPU experiment was run.

### Current runtime map

All three use `black-forest-labs/FLUX.2-klein-base-4B` at revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, `Flux2KleinPipeline.from_pretrained(..., torch_dtype=torch.float16, local_files_only=True)`, followed by `enable_model_cpu_offload(gpu_id=0)` and `load_lora_weights`. No inference quantization is configured. BF16/quantization in training configurations does not describe the serving pipeline.

| Concern | Hair | Makeup | Nails GPU |
| --- | --- | --- | --- |
| Server | `scripts/kaggle_inference_server.py`, `FluxRuntime` | `scripts/makeup_inference_server.py`, `MakeupRuntime` | `scripts/nails001_local_inference_server.py`, `NailsRuntime` |
| Selected adapter | TRAIN-001 step 250; TRAIN-002 step 500 only with the existing optional registry | MAKEUP-001 step 250 | NAILS-001-LOCAL-v1 step 50, Red/Black only |
| Hash source | Hair registry and adapter metadata; checkpoint verified before load | `makeup_contract.py` verifies checkpoint, metadata and ten reviewed preset hash | `nails/contract.py` verifies immutable checkpoint size/hash |
| LoRA file | `adapter.safetensors` | `adapter.safetensors` | `nails001_local_v1.safetensors` |
| Input/preprocessing | Backend and server aspect pad portrait to 512 RGB; server validates JPG/PNG, size and EXIF | Same portrait pad, reviewed preset ID | Backend prepares a localized 512 RGB nail crop; server accepts exactly 512 PNG and does not pad it |
| Inference | Fixed catalog prompt, 512, 20 steps, guidance 4.0, new CUDA generator seed 1977 | Same numerical settings, ten fixed Makeup prompts | Same numerical settings, two fingertip prompts |
| Output/postprocessing | RGB PNG data URL, dimensions and Hair adapter/style/runtime metadata | Same image envelope; strict Makeup adapter/Base/preset metadata | Same image envelope and strict Nails metadata; local backend reconstructs and composites the crop |
| Remote contract | `GET /health`, `POST /generate`, multipart `image`/`style_id`, constant time `X-API-Key` comparison | Same routes/form/header with independent key | Same routes/form/header with independent key |
| Startup | Hair bootstrap, port 8765, Kaggle `HAIRCAPSTONE_API_KEY`, pinned Base cache, one Uvicorn worker and Cloudflare Quick Tunnel | Makeup bootstrap, 8766, `MAKEUP001_API_KEY`, verified private bundle, one worker/tunnel | Nails bootstrap, 8767, `NAILS001_API_KEY`, verified private bundle, one worker/tunnel |
| Switching/residency | Keeps a pipeline object; unloads then loads one adapter, restores TRAIN-001 on switch failure; inactive adapters are disk paths/metadata, not cached inactive pipelines | Keeps pipeline and one adapter, no feature switching | Keeps pipeline and one adapter, no feature switching |

All pipeline objects persist for their server lifetime, but CPU offload moves components between host RAM and GPU. None keeps the entire foundation permanently on GPU or explicitly parks three inactive model copies in RAM. There is no explicit full pipeline disposal, unload or CUDA cache cleanup on request failure/shutdown in these servers; Hair explicitly unloads LoRA weights during switching. Makeup/Nails shield background inference on cancellation and hold their lock until the GPU thread finishes; Hair currently lacks that cancellation guard. Keep this distinction when adapting code.

### Foundation and adapter compatibility

The exact pinned [model index](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B/blob/a3b4f4849157f664bdbc776fd7453c2783562f4d/model_index.json) identifies `Flux2Transformer2DModel`, `AutoencoderKLFlux2`, `Qwen3ForCausalLM`, `Qwen2TokenizerFast` and `FlowMatchEulerDiscreteScheduler`. All servers load that snapshot without substituting components. Sharing the foundation, VAE, text encoder, tokenizer and scheduler is therefore a credible candidate. Scheduler state and offload hooks still require serialized execution and runtime validation. Identical saved weights do not guarantee identical execution across library versions.

Read only inspection of the four existing checkpoint headers (default TRAIN-001, optional TRAIN-002, Makeup V2 bundle, Nails V2 bundle) found **160 FP16 tensors each, identical tensor keys/shapes and rank 16 dimensions**. Every file is 46,223,600 bytes. The SHA-256 of sorted JSON mapping tensor names to `(dtype, shape)` is `4a993dfba0823e5fae29c278f264577ea8f7b8bad1cb45385ad4782a6e7cbb23` for all four. This compares layouts, not learned weight values or inference output. The three default files total 138,670,800 bytes, about 132.25 MiB on disk, not measured loaded GPU/RAM overhead. Headers were read with standard library `struct`/`json` and ZIP streams; no model library or weights were loaded.

Keep prompts, style registries, adapter validation, preprocessing and output provenance feature specific. Do not fuse adapters, change scales, preload every adapter, introduce quantization or use untested hotswap APIs. The existing Hair unload/load pattern is the starting candidate, not proof that Makeup/Nails can switch safely. Hair's live TRAIN-001/002 smoke used one foundation and restored byte identical Hair output; no Hair/Makeup/Nails switch has run.

### Dependency compatibility

| Dependency | Current Hair and Makeup requirement | Current Nails GPU requirement | Finding |
| --- | --- | --- | --- |
| Torch/CUDA | Existing Kaggle build retained, Hair constrains Torch; Makeup also constrains installed torchvision/torchaudio | Existing Kaggle build retained with companion constraints | Reported successful sessions include Torch 2.10.0+cu128/CUDA 12.8; no universal Torch pin or future availability guarantee |
| Diffusers | `0.40.0` | Git commit `c943837899b16cbae2f619b8dd4f7bb6f07dd81a`, bootstrap requires `0.39.0.dev0` | Exact requirements conflict |
| Transformers | `5.0.0` | `5.5.3` | Exact requirements conflict |
| Accelerate | `>=1.10,<2` | `1.13.0` | Direct pins overlap |
| PEFT | `>=0.17,<1` | `0.18.1` | Direct pins overlap |
| HF Hub | `>=1.23,<2` | `1.23.0` | Direct pins overlap |
| Safetensors | `>=0.8,<1` | `>=0.8,<1` | Same range, final resolved version unknown |
| NumPy | No explicit inference pin | `1.26.4` | No direct Hair/Makeup conflict; transitive compatibility needs install/import gate |
| FastAPI/Uvicorn/multipart/Pillow | `>=0.111,<1` / `>=0.30,<1` / `>=0.0.22,<1` / `>=10.1,<13` | Same ranges | Same ranges, reproducible common resolution still required |

Hair/Makeup share `scripts/kaggle_inference_requirements.txt`; Nails uses `scripts/nails001_inference_requirements.txt`. These files cannot be installed unchanged together into one environment. A unified runtime needs its own tested dependency lock. Start the experiment with the Nails evaluated commit and Transformers 5.5.3, because that path explicitly verifies those versions; validate Hair/Makeup on it rather than declaring it compatible. Do not downgrade the existing services. If that candidate fails, test the Hair/Makeup stack against Nails only as a bounded alternative, preserving output settings.

Hair/Makeup bootstrap code removes old optional torchao below 0.16 to avoid PEFT import failure; no serving path uses torchao quantization. Nails does not include that removal. Makeup's prior CUDA memory statistic reset failed before inference and is now optional; equivalent telemetry in a trial must not block generation. Changing package versions can affect safetensors conversion, offload hooks, scheduler defaults and output, despite compatible adapter layouts.

MediaPipe, OpenCV and Ultralytics are **not GPU service requirements**. Nails MediaPipe localization and isolated YOLO segmentation/refinement stay local. The recorded segmenter environment has Ultralytics 8.3.244, CPU Torch 2.10.0 and NumPy 2.4.6; the GPU NumPy 1.26.4 pin is separate. Exact current MediaPipe/OpenCV pins are not established by the GPU manifests. There is no reason to combine those vision environments with the Kaggle inference environment.

### Kaggle resource evidence and unknowns

| Evidence | What it establishes | Limit |
| --- | --- | --- |
| [TRAIN-002 switch smoke](../experiments/TRAIN-002-switch-smoke.md) | Python 3.12.13, Torch 2.10.0+cu128, T4 14.56 GiB reported VRAM; three Hair requests 62.68 to 64.93 s, **8,302.2 to 8,304.3 MiB PyTorch allocated peak**, restored output hash | Synthetic portrait; not total GPU memory, cross feature switching or a common dependency stack result |
| [Makeup integration](../experiments/MAKEUP-001-integration.md) | Reported five component loading stage 39.9 s and public health; optional telemetry failure reproduced/fixed | No corrected generated-image artifact or inference memory measurement in that record; 39.9 s is not complete bootstrap time |
| [Nails live handoff](../experiments/NAILS-001-hybrid-live-handoff.md) | T4, evaluated versions, model load 52.98 s; Hand A Red/Black app requests 378.969/382.375 s, five sequential crops, exact adapter provenance | No unified memory peak or generalization proof; geometry later changed locally |
| Prior training records | 13,531 MiB whole GPU training peaks | Training numbers must not be presented as serving peaks |
| Bootstrap storage checks | Hair needs at least 40 GiB free scratch or a larger repository estimate; Makeup/Nails each check 30 GiB | Guard thresholds, not measured model size or actual disk use |

Hair currently uses `/tmp/haircapstone-hf-cache`; Makeup/Nails use `/tmp/hf-cache`. Running all launchers can duplicate downloads and replace conflicting package versions. A new bootstrap should download/reuse one snapshot, using the existing Makeup/Nails component patterns including `text_encoder/*` generation configuration, in one cache. Do not extract existing private bundles over one another: their root `bundle.json` and adapter paths collide. Verify them independently and assemble a new manifest with distinct adapter paths.

Unified CPU RSS/peak RAM, GPU allocated/reserved/whole device peaks, switch overhead, repeated switch leak behavior, selected snapshot bytes/free disk, dependency/download/total startup time and current account quotas are **UNKNOWN**. Record these in the gate. One T4 has the historical capacity above; a second Kaggle GPU is not automatically pooled, and current code selects only GPU 0. [Kaggle notebook documentation](https://www.kaggle.com/docs/notebooks) describes finite notebook sessions and GPU quotas; the actual session allocation/remaining quota needs the Supervisor's UI check. [Cloudflare Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/) provide temporary URLs without an uptime SLA. The one notebook workflow is a capstone session workflow, not permanent hosting.

### Options considered

| Strategy | Resource/complexity assessment | Recommendation |
| --- | --- | --- |
| A, three full models resident | Duplicates identical foundation/text encoder/VAE weights. Existing paths configure CPU offload for a T4; they do not demonstrate three full GPU resident copies. Combined VRAM/RAM not measured. Three CPU offloaded pipelines still duplicate host weights | Reject as initial design; no evidence that three full copies fit |
| B, shared foundation switching | One existing type of pipeline, one loaded adapter, serialized unload/load using the Hair precedent. Small disk assets; avoids foundation reload per request | Preferred conditional candidate; common stack and cross feature output/recovery gates required |
| C, on demand full model loading | Dispose/rebuild pipeline when feature changes, cache files on disk. Fresh load is extra work; existing component load measurements are tens of seconds, actual switch cost unknown. Requires correct disposal/hooks and does not resolve dependency conflicts | Backup experiment only if B fails; do not build this machinery now |
| D, hybrid | One CPU offloaded foundation with feature adapters loaded from disk is the practical memory policy for B. A separate resident Nails model or CPU cache of three foundations has no evidenced benefit | Use existing CPU offload within B, not another model tier/cache system |

### Requirements for any later implementation

- **AC-1:** One new notebook/bootstrap, inference process and tunnel serve all three supported remote features with one verified Base snapshot.
- **AC-2:** Existing prompts, steps, seed, guidance, padding/crop boundary, styles and response/provenance contracts are preserved; single adapter state is verified under one lock.
- **AC-3:** Nails localization, segmentation, refinement, deterministic styles, reconstruction and final compositing remain in the application backend.
- **AC-4:** Feature asset failures stay scoped where the foundation is healthy; busy requests, cancellation and recovery cannot expose the wrong adapter.
- **AC-5:** Application cutover is incremental and reversible; separate runtimes/clients and legacy routes remain until live validation succeeds. No common dependency or memory claim is verified by source inspection alone.

### Decision proposed and minimal server contract

```text
Next.js -> shared client -> central FastAPI -> existing feature handlers
  -> Hair remote client ------> <root>/hairstyle/generate
  -> Makeup remote client ----> <root>/makeup/generate
  -> Nails crop remote client -> <root>/nails/generate
                                one Kaggle FastAPI process
                                one global inference/switch lock
                                one pinned CPU offloaded FLUX pipeline
                                one selected LoRA at a time
```

Use `GET /health` for foundation state, busy state, actual active adapter and per feature availability/error category; distinguish verified/available adapters from the single currently loaded adapter. Generation keeps multipart `image` and `style_id`, `X-API-Key`, feature style allowlists and existing JSON images/metadata/generator names. The remote Nails route advertises only Red/Black; the application still exposes all five Nails styles. Remote `/features` is optional; application discovery remains the existing central registry, so do not create another style source of truth. Do not import and mount all three existing ASGI applications, which would retain independent pipeline loading and locks.

Initial cutover can set `FLUX_REMOTE_URL=<root>/hairstyle`, `MAKEUP_REMOTE_URL=<root>/makeup`, `NAILS_REMOTE_URL=<root>/nails`, with one shared secret value. Each existing client already appends `/generate`; no client rewrite is required. Later `AI_REMOTE_URL`/`AI_REMOTE_API_KEY` can supply those derived destinations in the existing environment factories, with explicit per feature settings taking precedence for rollback. Clear an old override when selecting the shared default. Retain `GENERATION_ENGINE`, `MAKEUP_GENERATION_ENGINE` and `NAILS_PREVIEW_MODE`; URL sharing does not replace mock/hybrid mode selection. No shared universal remote client is needed because validation/preprocessing/provenance differ. Add the registry based expected adapter/Base/style provenance check to Hair before shared runtime cutover; Makeup and Nails already check their pinned contracts.

### Failure isolation and consequences

| Failure | Minimal behavior |
| --- | --- |
| Hair/Makeup/Nails asset or preset verification fails | Catch per feature validation/import failure; mark that remote feature unavailable, return 503 there, initialize other verified features. Foundation initialization must not require TRAIN-001 merely because the old Hair loader does |
| Adapter switch fails | Hold the lock, remove partial adapter and restore the previous verified adapter. Never generate after a failed switch. Return a controlled failure; disable the faulty feature until repaired. If restoration cannot establish safe state, mark all shared GPU paths unavailable |
| CUDA OOM | Fail the request, retain lock through cleanup, discard temporary state and attempt only bounded restoration/reload if safe. Continue other features only after recovery is verified. Fatal CUDA context corruption needs process/session restart and cannot be isolated by a feature flag |
| Client/tunnel timeout or disconnect | Reuse Makeup/Nails shield-and-wait behavior so background GPU work finishes before releasing the lock. Do not start another adapter switch while it computes. No silent retry or fallback; other requests get 429 until free |
| Foundation/dependency/process/tunnel failure | All remote model routes share the outage; this cannot be eliminated with one runtime. Local Nails renderer styles remain independent |

One active GPU request at a time is intentional. A five nail request remains five crop calls; no batching, hand level GPU job or GPU preprocessing migration is proposed. Other features may receive 429 between/while crop work runs. Preserve existing 180 s Hair/Makeup and 300 s Nails per crop client deadlines during comparison; measure tunnel and full hand completion before adopting any timeout change. Single runtime saves duplicated foundation resources, not inference time or throughput.

### Required experiments, not run

1. **Common stack and individual equivalence gate.** In one disposable Kaggle session, retain its CUDA Torch build, install the proposed common stack, record imports/versions and validate all checkpoint/preset hashes. For a fixed real Hair portrait, Makeup portrait and Nails crop, compare candidate outputs with isolated references from each current stack at the approved settings. Also preserve isolated candidate-stack repeats as the switching baseline. Verify active adapter, pixels/visuals and numerical settings. Collect Base download bytes, free disk, stage startup times, CPU RSS and GPU allocated/reserved/whole device peaks. If version changes alter feature output materially, stop and evaluate the bounded alternative stack before a unified build.
2. **Switch/state/recovery gate.** On one loaded Base run Hair -> Makeup -> Nails -> Hair -> Makeup, then repeat a small fixed cycle. Confirm first/restored outputs match deterministic isolated repeats or demonstrate the same measured numerical variation as isolated repeats. Track RAM/VRAM drift and switch latency. Test a missing/corrupt adapter, forced switch exception, concurrent request and cancelled request; test OOM recovery with an injected error first rather than deliberately exhausting the notebook. Actual CUDA recovery remains unverified unless safely observed. Optional TRAIN-002 participates only if that registry is enabled.
3. **One tunnel/application acceptance gate.** After 1/2 pass and a separately authorized candidate server exists, use the central frontend/backend for Hair, Makeup and all five Nails styles. Confirm five model crop calls, unchanged outside-mask pixels, correct provenance, busy/error recovery and observed latency across the public tunnel. This is the previously deferred live central gate plus unified acceptance, not a prerequisite to writing this audit.

These three gates can use one controlled session, but reference processes must run sequentially and be stopped before the shared candidate; do not keep three foundation copies alive during measurement. No general benchmark suite, new training, quantization test or scheduling framework is needed.

### Build plan and migration plan

**Strategy:** Add a candidate beside working services and migrate one feature at a time, after Supervisor authorization and the relevant gates. No implementation has begun.

1. Prepare the isolated gates above and independently verified common dependency resolution (AC-2/4/5), using read only original adapters. Do not update existing manifests/environments.
2. Add only new `scripts/unified_inference_server.py`, `scripts/unified_inference_bootstrap.py`, `scripts/unified_inference_requirements.txt` and `scripts/package_unified_inference_runtime.py` (proposed paths). Reuse feature contracts/catalogs and artifact verifiers; one Base load, per feature validation, global shielded lock and safe unload/load transitions (AC-1/2/3/4). Unit tests fake model boundaries; no live proof is claimed from them.
3. New bundle contains separate adapter paths and reviewed catalogs/presets with a new integrity manifest; no optimizer/data/training payload. Bootstrap verifies assets/Secrets/CUDA, installs one stack, downloads one snapshot, reports foundation and per feature readiness, starts one worker/tunnel and prints configuration without key values (AC-1/4). A missing feature must not prevent healthy feature readiness; all three are required for the desired successful demo startup.
4. Run gates 2/3, keep original references and fallback inputs. Point Hair first, then Makeup, then Nails to the corresponding URL prefix. Recheck existing regressions and live results at each step. Add optional shared URL/key defaults only after these paths pass; retain explicit overrides and existing client validations (AC-2/3/5).

**Rollback:** Restore that feature's original URL/key and restart the local backend, with its separate Kaggle service alive or restarted from preserved inputs. Existing temporary tunnel addresses are not durable rollback assets. Do not delete originals or flip all three configurations at once. No frontend change is needed.

**Risks:** Common package output drift, offload/adapter state leakage, CPU RAM pressure, shared CUDA failure and longer busy periods. If gates fail, keep separate services. A single public proxy over three existing model processes can conceal the dependency/resource problem and is not the recommended consolidation.

### External actions and follow-up

**Nothing needs to run in Kaggle during this audit.** When the gate is separately approved, create one new private GPU notebook, select T4 where available, enable Internet, attach private verified adapter/code inputs and enable one new shared `AI_REMOTE_API_KEY` Secret of at least 24 random characters (optional `HF_TOKEN` if required for download). Check current accelerator/quota/RAM/disk, run the staged probe/bootstrap and return sanitized environment, memory, timing, hash and recovery records. Keep original notebooks/inputs unchanged. No unified bundle or launch cell exists yet, so this report is not a ready-to-run notebook handoff.

### Rationale

The foundation revision, pipeline class, inference precision/settings and checkpoint layouts align across all three. Hair's live adapter restoration is a useful precedent. That favors B with the current CPU offload memory policy over loading three identical foundations or repeatedly rebuilding them. Conflicting dependency pins and absent cross feature runtime/RAM/output/recovery evidence prevent an unconditional feasibility claim. The next step is the isolated compatibility gate, not an application refactor or an immediate production cutover.
