# Deployment 01 preparation

2026-09-28. **IN PROGRESS; LOCAL VERIFIED; FRESH SESSION REHEARSAL NOT STARTED.** Gate 3 remains passed for its reviewed live integration. `CAPSTONE_DEPLOYMENT_READY` is not claimed. The original Nails transport interruption remains UNKNOWN; this change instruments the next occurrence rather than assigning a cause.

## Phase A request and retry audit

Actual Nails path: Next.js `frontend/lib/api.ts` sends a multipart hand/style to central `/features/nails/generate`; `backend/app/main.py` dispatches to `generate_nails`; `HybridNailsPipeline.run` performs local localization, segmentation and refinement, prepares mappings, then awaits `RemoteLocalizedNails.generate` sequentially for each crop. Each crop is encoded as a 512-square PNG and POSTed through the configured tunnel to unified `/nails/generate`. Its FastAPI handler validates auth/style/image/readiness and enters the Gate 2 owner. One ownership lock covers adapter verification/switch, inference, synchronization, output verification and cancellation drain. Reconstruction and mask compositing remain local. Renderer-only styles never enter the crop HTTP loop.

| Boundary | Previous failure behavior / information lost |
| --- | --- |
| Local hand vision / crop validation | Rejection returns 422 before GPU calls. Separate from the Gate 3 observed 502. |
| First reduced-step crop preflight | GET `/health`, timeout 10 s; support is cached after successful verification. A transport failure here was indistinguishable from a generation POST transport failure. |
| Crop POST transport | Fresh HTTPX client per crop, 300 s timeout configuration for connect/read/write/pool; not a 300 s total hand deadline. Hair/Makeup use 180 s. No explicit transport retries. |
| Tunnel / worker connection | Client RequestError covers connection, timeout, read/write/protocol errors. The previous code chained it into a generic NailsGenerationError without logging its type, crop, timing or receipt stage. |
| Non-200 worker response | 401/429/503 get helpful messages; other statuses get a generic status message. All become central 502. Upstream raw bodies are not shown. |
| Remote PNG / provenance validation | Invalid image/model/settings become a controlled NailsGenerationError and central 502. |
| Local reconstruction / final mask | Separate local exceptions, not proof of a transport failure. |

The observed Gate 3 message specifically came from the HTTPX RequestError catch (either preflight or POST), but the exception class was not retained. Two successful crop records show only that those calls completed. They cannot prove whether a later request was accepted, still running, completed with a lost response, or never reached the worker. No component is identified as the cause.

**Retry decision: no automatic retries for any category in this milestone.** None existed previously. Read/write timeouts, protocol disconnects and proxy interruptions are ambiguous: Uvicorn may continue inference even when the client has stopped waiting. If HTTP task cancellation occurs, the Gate 2 shield and wait loop retains ownership until the GPU boundary drains. A simultaneous request receives 429 while ownership is held; a later identical request can generate again after release. No idempotency or deduplication exists. The prior completed-crop status list alone cannot identify a repeated logical request. Connection/pool failures and the known worker 429 may support bounded retry in principle, but a new retry is unnecessary for this demo scope. Deterministic 4xx and inference/unready failures are not retried. Manual retry requires checking worker readiness and idle state first. Missing bounded history does not prove a request was never accepted. No distributed jobs or idempotency framework was added.

## Implemented preparation

* `backend/app/generation/diagnostics.py`: pure ASGI request identity/logging and context scopes. UUID validation prevents arbitrary supplied strings entering logs. The wrapper does not release or change GPU ownership.
* `backend/app/generation/remote_http.py`: one attempt, existing HTTPX request/timeouts; response hook records headers before body buffering. Logs category/class, boundary, feature/style, correlation/request UUID, attempt 1, crop index/finger, elapsed time, status and response receipt flags. No URL, exception string, raw body, image or key is logged.
* Existing Hair/Makeup/Nails clients use that request observer. Public errors and inference contracts remain unchanged. Nails orchestration adds only crop scopes/events, not crop/model/compositor changes.
* Unified worker adds UUID/crop propagation, bounded last 60 accepted/rejected/cancelled HTTP records, last 30 existing GPU completion records, safe inference events, busy state and `diagnostics_version=deployment-01`. HTTP send flags mean the ASGI send completed, not proof the browser received the response. An observed disconnect is recorded only if ASGI receive reports it; false does not prove no proxy disconnect occurred. Failure logs omit raw internal exception strings.
* `backend/app/deployment.py` and additive `/deployment/readiness`, `/deployment/diagnostics[/UUID]`: check the running backend's unified client configuration, protected remote auth, Base/readiness/load count, pinned revision, supported features, idle state and configured Nails step support. Image-free, no silent fallback. Diagnostics query bounded history; no inference or retry is initiated.
* `scripts/demo_readiness.py`: one safe pre-demo command, optional UUID lookup or snapshot/output. `scripts/deployment01_smoke.py`: four central requests, fresh-worker requirement, stop on first failure, no retries; records safe application metadata and per-crop worker counts without saving input/output images.

## Repeatable Kaggle packaging

`scripts/package_deployment01.py` derives one new private package from the immutable accepted Gate 3 v2 bundle. It adds the diagnostic source and the existing approved reduced-step Nails support. Source model methods, Gate 2 owner, weights, reference inputs, bootstrap and dependency requirements remain byte-identical to the original package. The original private bundle/notebooks and original three runtimes are not overwritten. The new notebook runs the same reviewed bootstrap once, loads one Base once, and needs no later latency-update cell. Package creation/upload is a one-time handoff, not a step for every demo.

Final package `artifacts/deployment01_20260928_v2.bin`: **128,962,896 bytes**, SHA-256 `68f6c9eb2bc0ce12b2c9c6d89e33f22898fb201b33a792887f6c5967ad16ec4e`. [Safe source inventory](deployment01-bundle.json). It contains private adapters and reference images and remains ignored by Git. No Base snapshot, credentials or tunnel URL is packaged. `notebooks/deployment01_kaggle.ipynb` contains four exact cells, three for startup and one after application rehearsal to preserve status/probes/server logs and source hashes. It refuses reused output directories.

## Local evidence

* Focused transport/readiness, Gate 3, remote contracts, central paths, Nails hybrid and latency checks: **109 passed**. The final full run includes the rehearsal fresh-worker and crop-count assertions.
* Final full backend (`cd backend; python -m pytest tests -q`): **299 passed** in 41.35 s, one existing multipart deprecation warning. No frontend source changed; frontend tests/build were not repeated.
* Bundle outer/member/source hashes, CRC, unique safe inventory and unchanged original methods/weights/dependency pins verified. Four generated notebook cells compile and reference the exact package SHA.
* Extracted assembled worker and `verify_bundle()` imported successfully in a fresh local subprocess, without Base loading (`foundation_load_count=0`, ready false). This also checked the Makeup preset JSON required by the prior update correction.
* The existing backend `.venv` lacks MediaPipe on this machine; the previously successful system `python` environment is the current demo interpreter. The runbook uses it and preserves the isolated Nails segmentation interpreter. No environment was modified.

No fresh Kaggle session, new public tunnel or new diagnostic GPU worker has been started during preparation. The next action is the [short deployment runbook](../guides/capstone-deployment01.md). Return notebook `live-evidence.zip` plus local `application.json`. On an interruption, stop and return diagnostics; do not repeatedly retry until it disappears. Only independent review of that fresh-session rehearsal can establish `CAPSTONE_DEPLOYMENT_READY`.
