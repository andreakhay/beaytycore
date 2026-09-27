# 0001. Shared application architecture

**Date**: 2026-09-27  
**Status**: Proposed, awaiting Supervisor approval for a shared GPU runtime

## Summary

Use the existing Next.js app and FastAPI application as the one public system. FastAPI owns upload checks, feature selection, result formatting, and the Nails CPU pipeline. The three trained LoRAs can eventually share one loaded FLUX.2 Klein Base in one GPU process, with one adapter active at a time. Keep the current independent GPU services until a bounded switch and output test proves that consolidation preserves their behavior.

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

Keep the existing feature routes. They already form a clear, stable API, so a generic `/ai/generate` router adds indirection without removing meaningful duplication. The browser selects the feature route and a style ID, sends `multipart/form-data` with `image` and `style_id`, and receives the existing `GenerateResponse`. It never receives GPU credentials, adapter paths, or model prompts. A shared frontend upload and result component is a later UI refactor, not a prerequisite for backend consolidation.

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
