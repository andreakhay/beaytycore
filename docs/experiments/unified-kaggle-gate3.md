# Gate 3 unified Kaggle service and application integration

2026-09-28. **DONE; LIVE APPLICATION VERIFIED; GATE_3_PASSED.** Gate 1 and Gate 2 are passed for their reviewed fixed cases. Gate 3 was independently checked using the actual pages, central FastAPI, one unified Kaggle worker, and the returned notebook evidence. The existing three GPU servers remain intact as rollback. [Final numeric review](unified-kaggle-gate3-live-review-20260928.json).

## Implemented candidate

Next.js feature pages continue to call the shared client and central FastAPI `/features/{feature}/generate`. Setting both `AI_REMOTE_URL` and `AI_REMOTE_API_KEY` selects the same remote root with `/hairstyle/generate`, `/makeup/generate` and `/nails/generate` suffixes. The existing feature clients still own their own request formatting, response checks and timeouts. When both unified settings are absent, their original URL/key settings apply. A half configured unified pair fails at configuration instead of falling back silently. Existing application routes and Nails hybrid CPU stages are unchanged.

`scripts/unified_gate3_server.py` is a new FastAPI worker. It loads the pinned Base once in FP16 with CPU offload, verifies all enabled approved adapters, loads TRAIN-001 first and owns a single pipeline. It subclasses the Gate 2 `SharedExperiment` owner for ordinary unload/load, exact active LoRA tensor/layer verification, foundation identity, restoration/fail-closed switching, one async ownership lock and shielded thread drain on cancellation. It invokes the original `FluxRuntime.generate`, `MakeupRuntime.generate` and `NailsRuntime.generate`; dynamic style contracts validate the existing result metadata, PNG and approved settings. Same-adapter requests verify active state without unloading/reloading. All generation remains serialized. Inference failures leave the worker unready because adapter/GPU state may be uncertain. Controlled switching failures restore the previous verified adapter when possible; failed restoration remains unready.

The server exposes public `GET /health` with process/Base/readiness, load count, active feature/adapter and supported features; protected `GET /status` with the last 30 safe request records, adapter provenance, timing and sampled memory; and authenticated multipart `POST /{feature}/generate`. The key comes from `AI_REMOTE_API_KEY` Kaggle Secret/environment. Invalid feature/style, malformed upload, missing key, unready and inference/switch failures return controlled HTTP errors without exposing paths or internal bodies. One Uvicorn worker is required. HTTP cancellation uses the Gate 2 shield-and-wait ownership boundary; repeated ASGI HTTP handler cancellation has been checked locally, while actual proxy disconnect behavior still needs live validation. Busy concurrent HTTP requests return 429 without switching the active adapter; they may be retried after the current request completes.

Current default `backend/app/style_registry.json` has three enabled Hair styles on **TRAIN-001 only**. The existing optional TRAIN-002 registry is separate and not bundled into the Gate 3 default dataset. The new server checks its enabled Hair registry against attached adapter directories and refuses missing assets. An opt-in future TRAIN-002 run would require its approved registry and artifact in the private notebook input and backend configuration. No adapter mapping is invented. Makeup presets and the two Nails model styles use their existing catalogs. Nude Pink, French Tip and Pink Ombre remain renderer-only in local FastAPI.

## Isolated files and handoff

| File | Purpose |
| --- | --- |
| `scripts/unified_gate3_server.py` | New shared foundation HTTP worker; no original runtime edits |
| `scripts/unified_gate3_bootstrap.py` | Exact Gate 2 environment, one Base download/server/tunnel and safe startup report |
| `scripts/unified_gate3_requirements.txt` | Reuses the reviewed Gate 2 requirements exactly |
| `scripts/package_unified_gate3.py` | New private bundle based on the immutable reviewed Gate 2 bundle |
| `notebooks/unified_gate3_kaggle.ipynb` | Four cells: verify/extract, launch, setup evidence, post-application evidence |
| `backend/app/generation/remote_destination.py` | Shared URL/key selection with explicit legacy configuration rollback |
| `backend/tests/test_unified_gate3.py` | Fake GPU server and central application integration checks |
| `docs/guides/unified-kaggle-gate3.md` | Exact Kaggle/application/live handoff |

Final private handoff bundle: `artifacts/unified_gate3_20260928_v2.bin`, **128,958,525 bytes**, SHA-256 `a3d73ce4ac0995a17bfa6a7c48253e2a2fa7db9ae635941295804d60dcb03683`, 45 members. It adds Gate 3 sources and reviewed Gate 2 evidence to the trusted Gate 2 bundle. It contains the approved private adapters and fixed validation images, but no 15+ GiB Base, credentials or tunnel URL. It is ignored by Git and must be uploaded as a **private** Kaggle Dataset. Local archive CRC, unique inventory, all member hashes, safe extraction, Gate 1/2 artifact preflight and all four notebook cell parses passed. Exact Gate 2 dependency versions, including Diffusers commit and Safetensors 0.9.0rc1, are required. Base is downloaded/cached once in `/tmp/gate3-hf-cache`, separate from the adapter bundle.

## Validation before Kaggle

* `backend/tests/test_unified_gate3.py`: **13 passed** with fake model boundaries. Covers one Base startup/health, auth/status, all feature routes, dynamic style/provenance, same-adapter reuse, cross-feature switching, invalid feature/style/image, switch recovery/fail-closed, inference failure, HTTP busy and cancelled owner drain, shared URL/rollback, missing enabled Hair assets, and complete central FastAPI → new unified HTTP routes with synthetic Nails vision/compositing and renderer-only bypass.
* Full backend `python -m pytest tests -q`: **244 passed**; one existing multipart warning.
* Frontend lint and production build passed; shared API client tests: **11 passed**. No frontend source changed.
* These are local/mock checks. No Gate 3 Kaggle server, public tunnel, actual central application live request, real HTTP proxy disconnect or deployment has been run. No generated image quality claim is added.

## Live acceptance plan (completed below)

The [Kaggle/application guide](../guides/unified-kaggle-gate3.md) specifies Hair `crew_cut` → Makeup `natural_makeup` → Nails `classic_red` → Hair `crew_cut`, then Nails `nude_pink` renderer. The actual run and returned Cell 4 evidence are reviewed below.

For a capstone/demo, an accepted temporary Kaggle session and one configured URL may suffice while it remains alive. Persistent public deployment needs a durable GPU host, stable URL, availability/session management and operational validation; those are outside Gate 3 and no provider migration is underway.

## Live acceptance update, Nails crop rejection

The Supervisor reports successful Hair and Makeup generation through the running Gate 3 application. No returned Gate 3 archive or request provenance has been independently reviewed yet. Nails returns HTTP 422 with the existing message that fingernails are too close together. This message originates from `backend/app/nails/localized.py`, before any GPU crop request, rather than from the unified service. The supplied TensorFlow and MediaPipe startup logs do not establish a detector failure.

The crop and hybrid implementation was unchanged between the preserved baseline and the Gate 3 candidate. The existing integration record already documents that the model path rejects a whole hand if any detected nail cannot be isolated under the evaluated training geometry. The same error also covers candidates outside the image boundary or unable to contain the entire selected nail. The reported upload/style has not been supplied, so its exact rejection cause is NEEDS VERIFICATION.

A fresh CPU check using the real configured MediaPipe localizer and isolated YOLO segmenter accepted all five crops for both approved source identities `0000000` and `0000088`. Their respective crop sides were `[70, 62, 60, 60, 56]` and `[58, 58, 60, 60, 56]`. No remote inference was called. The known source path for the previously successful Hand A is `data/nails/work/source-frozen-v4/source/0000000.png`.

Added warning logging on failed crop search only: finger, candidate size range and counts for `image_boundary`, `target_not_contained` and `neighbor_support`. No images, paths, credentials or request contents are logged. Crop thresholds, accepted mappings, model settings, rejection behavior and the notebook bundle are unchanged. Synthetic crowded and border cases still fail before GPU calls; the accepted fixture retains all five exact crop sizes and emits no rejection log. The user's image is required, or the new rejection log after restarting local FastAPI, before deciding on a fix. Gate 3 remains pending Nails and complete live acceptance evidence.

## Exact uploaded hand reproduction

The Supervisor subsequently supplied the original hand image location matching the screenshot and selected Classic Red. The real local MediaPipe detector, isolated YOLO segmenter and current crop code reproduce the rejection deterministically. All five mask components pass mask validation. Candidate isolation fails on index, middle and ring; thumb and little succeed. Ring is the first failed component in the current iteration, but independent per-finger inspection found the other two rejected crops as well.

| Finger | Allowed square side range at normalized 512 px | Result |
| --- | --- | --- |
| Thumb | 67 to 89 | Accepted at 89 |
| Index | 77 to 103 | All 27 candidates include neighboring nail support |
| Middle | 83 to 110 | All 28 candidates include neighboring nail support |
| Ring | 76 to 101 | All 26 candidates include neighboring nail support |
| Little | 65 to 86 | Accepted at 86 |

The rejected searches report zero image boundary or target containment failures. The cause is the evaluated single nail context size and padded neighbor exclusion combined with the existing whole hand rejection policy. This is a documented input support limitation, not a changed dependency, detector crash or unified GPU response. No GPU request occurred during this reproduction. The exact same original image completed the real local hybrid Nude Pink renderer path with five nails and its original 462 by 663 output dimensions. The model and renderer paths therefore differ in accepted crop requirements. Private input, masks and diagnostic output remain ignored under `.tmp/nails-upload-diagnosis/`, outside Git.

No crop acceptance rule or model behavior was changed. Supporting this pose for Red or Black requires a separately evaluated local crop-policy adjustment; blindly removing neighbor checks or silently substituting the renderer is not an established fix. Gate 3 model-backed Nails live acceptance can still use the existing approved passing reference hand. This check establishes the reported upload's cause, not live unified Nails inference or Gate 3 passage.

## Subsequent authorized crop correction

The Supervisor explicitly requested removing excessive close-pose rejection. A local correction now preserves the original successful isolated crops, and selects the least neighboring context within existing size ranges when only neighbor exclusion blocked a complete target crop. Per-nail reconstruction and final mask protection remain the output boundary. All five nails on the exact reported image reach crop preparation; both approved reference hands retain exactly identical mappings and RGB crops. Full backend 248 passed. This supersedes the earlier unchanged-policy notes for previously rejected poses, without changing the remote service, models or settings. Detailed configuration, tests and live result are in [the correction evidence](nails-close-pose-crop-fix-20260928.md). Gate 3 overall acceptance remains pending.

## Live browser sequence on the unified worker, 2026-09-28

**LIVE APPLICATION PATH VERIFIED; KAGGLE CELL 4 ARCHIVE REVIEW PENDING.** The Supervisor restarted the same Gate 3 notebook and ran the reviewed Nails update cell. Its reported status was `READY_FOR_NAILS_LATENCY_COMPARE`. Independent public health and protected status checks found the worker ready, one Base load and supported Nails steps `[8, 12, 20]`. The local FastAPI feature discovery returned HTTP 200. The actual Next.js pages loaded their central styles at `http://localhost:3000` (13 Hair, 10 Makeup, 5 Nails), accepted the approved Hair/Makeup inputs and the Supervisor's original hand photo, and sent generation only to central `/features/{feature}/generate` routes. Headless Edge was used to drive those pages; no mocked inference was involved.

The same live worker then served Hair `crew_cut` (HTTP 200, visible result, 70 s), Makeup `natural_makeup` (200, 66 s), Nails `classic_red` (200 on retry, 258 s), and Hair `crew_cut` again (200, 70 s). The two Hair outputs have the same PNG SHA-256. Protected status records identify TRAIN-001, MAKEUP-001 and NAILS-001-LOCAL-v1 on the pinned Base with 20, 20 and 8 steps respectively. The successful Nails full-hand request produced five sequential 8-step GPU crop records. Renderer-only Nails `nude_pink` returned 200 and a visible result in 13 s; protected GPU request count stayed **10 → 10** and active feature stayed Hair. Foundation load count remained one and worker readiness remained true. The [sanitized numeric record](unified-kaggle-gate3-live-browser-20260928.json) contains input/output hashes, central statuses, times and adapter IDs; private images and the temporary URL/key remain outside Git.

The first model-backed Nails attempt returned a controlled central HTTP 502 after two successful GPU crops. The page showed “The Nails GPU service is unavailable or timed out. Please try again.” The exact underlying transport exception was not captured, so its cause is **UNKNOWN**. Protected worker status remained ready with correct Nails adapter provenance; retrying the same original hand completed all five crops and the result. This is a recoverable observed interruption, not evidence of consistently reliable tunnel transport. There was no silent route fallback and no worker restart.

Notebook Cell 4's safe HTTP probes, setup archive and full protected status were subsequently returned and independently reviewed below. The original three independent GPU runtimes and legacy backend routes remain available as rollback. Current work has not started deployment or GPU provider migration.

## Final Gate 3 evidence review

The returned private `live-evidence.zip` is 4,144 bytes, SHA-256 `845909dedb28cd6dbbe72b242a94c3e7c3f27568a9803b9657a1605e61159213`. Its seven unique safe members pass CRC. The setup manifest SHA matches the trusted Gate 3 private bundle; model ID/revision/index and the exact Python/package/CUDA environment match reviewed Gate 2. Public health reported readiness, one Base load and all three feature routes. The final protected status remained ready with one Base load and ten successful per-crop/request GPU records in the observed sequence: Hair, Makeup, seven Nails crops (two before the controlled 502 plus five on retry), Hair. Each record's adapter ID/SHA, style, Base revision, steps and HTTP 200 match the current feature contracts. Cell 4 returned wrong key 401, unknown feature 404, invalid style 400 and invalid image 400; the probes created no additional GPU records. No API key was present in the archive. The temporary URL is inside the private archive and is not committed.

The actual page results and protected status together satisfy the bounded Gate 3 acceptance: one notebook/URL/Base served Hair, Makeup and model-backed Nails; Hair generated the same PNG before and after feature switching; renderer-only Nails made no GPU call; the worker recovered from the observed transport interruption and stayed ready through the safe HTTP probes. The request owner/serialization, switch restoration and cancellation boundary were previously checked in Gate 2 and Gate 3 local tests. **GATE_3_PASSED for capstone-scale live integration.** The transient Nails 502 remains an operational reliability concern with an unknown underlying network exception. Real proxy disconnect, sustained multiuser load, every style, and durable hosting were not exercised. This acceptance is separate from Nail visual-quality improvement and public deployment. [Sanitized browser record](unified-kaggle-gate3-live-browser-20260928.json), [independent numeric review](unified-kaggle-gate3-live-review-20260928.json).
