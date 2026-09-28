# Gate 3 unified Kaggle service and application integration

2026-09-28. **IN PROGRESS; LOCAL/MOCKED VERIFIED; LIVE ACCEPTANCE NOT STARTED.** Gate 1 and Gate 2 are passed for their reviewed fixed cases. This is a new additive service and backend configuration path; the existing three GPU servers remain intact. **GATE_3_PASSED is not claimed.**

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

## Remaining live acceptance

Use the [exact Kaggle/application guide](../guides/unified-kaggle-gate3.md). One notebook must report public readiness and Base load count one. Through the actual pages and one URL, run Hair `crew_cut` → Makeup `natural_makeup` → Nails `classic_red` → Hair `crew_cut`, then Nails `nude_pink` renderer. The model-backed Nails request may make multiple sequential crop calls; this is the existing hybrid behavior. Record central API statuses/results, adapter provenance and protected server status counts. Verify renderer adds no GPU request. Notebook Cell 4 runs safe HTTP 401/404/400/400 probes and verifies readiness/request counts remain unchanged. Send the generated `live-evidence.zip` and non-private application status summary for independent review. **Only after this live evidence is reviewed can Gate 3 pass.**

For a capstone/demo, an accepted temporary Kaggle session and one configured URL may suffice while it remains alive. Persistent public deployment needs a durable GPU host, stable URL, availability/session management and operational validation; those are outside Gate 3 and no provider migration is underway.
