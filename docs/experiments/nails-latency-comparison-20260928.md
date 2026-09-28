# Nails latency comparison

2026-09-28. **DONE; LIVE FIXED-CASE VERIFIED.** Supervisor authorized comparing 12 and 8 inference steps against the current 20-step result before selecting a faster setting. The corrected worker starts, both full-hand comparisons succeed, and the local application now uses 8 steps. This is a bounded inference experiment, not retraining or a Gate 3 pass.

## Measured starting point

The exact reported close-pose hand completed Classic Red through central FastAPI and the unified T4 service at 20 steps: 365.375 seconds wall time, 322.81 seconds model generation across five sequential crops (62.197–66.839 seconds each). Final output changed zero pixels outside the refined nail mask. Private input/output and the report remain ignored in `.tmp/nails-upload-diagnosis/`; do not put them in Git. See [baseline correction evidence](nails-close-pose-crop-fix-20260928.md).

## Implemented comparison path

- `scripts/unified_gate3_nails.py` extends the existing Nails runtime only for explicit 8/12-step requests. The 20-step path delegates to the unchanged original generator. Base, adapter, prompt, guidance 4, seed 1977, 512×512 input/output, FP16 CPU offload and all local Nails processing remain unchanged.
- Unified HTTP accepts Nails-only `inference_steps` values 8, 12, 20. Health advertises these choices; protected audit and generation metadata record actual steps. Hair/Makeup still require 20. Shared ownership, switching and provenance checks remain enforced. The unchanged Gate 1 validator is reused for other fields/image checks after independently checking actual step provenance; the response is never rewritten.
- Backend `NAILS_INFERENCE_STEPS` chooses the remote client setting; unset remains 20. Fast requests check advertised support before sending any crop. Unsupported older workers fail visibly before inference; no legacy fallback. Each crop response must match the requested step count. Central model responses expose `metadata.inference_steps`.
- `scripts/nails_latency_update.py` verifies the original extracted bundle and code patch, creates an isolated small source tree with references to the existing adapters, drains the original worker gracefully, and starts one updated worker with the cached Base. No installs, downloads, tunnel replacement, model copies or changes to the original bundle. A failed startup restores the original 20-step worker after draining the candidate. Generated [one-cell update](../../notebooks/nails_latency_update_cell.py) embeds only hashed source, no assets/secrets/URLs. Regenerate with `python -m scripts.package_nails_latency_cell` from repository root. The Gate 3 packager includes new imports for future bundles; existing v2 bundle/notebook remain untouched.

## Local validation

Full backend at the first completed checkpoint: **259 passed**, one existing multipart deprecation warning. Two subsequent notebook startup/fallback tests also passed. Focused latency/service/hybrid suite: **41 passed**, including actual central handler → real remote client → fake unified HTTP boundary for 20/12/8, unchanged parameters, wrong-step rejection, unsupported-worker preflight, invalid steps, and source integrity. Notebook-controller tests verify refusing unrelated PIDs, preserving original assets, cached-Base startup and original-worker restoration. Generated cell compiles; private assets are not in its payload. This does not measure faster T4 inference or polish quality.

Frontend API client regression: **11 passed**. No frontend source changes; lint/build were not repeated for this backend/runtime-only experiment.

## Exact running-notebook handoff

1. Wait until no application generation is running. Open `F:\HAIR\notebooks\nails_latency_update_cell.py`, copy its **entire contents** into **one new code cell in the currently running Gate 3 Kaggle notebook**, and run that cell. Do not rerun original setup or create/upload another dataset.
2. Keep the existing `AI_REMOTE_API_KEY` Secret enabled. The original T4 notebook, Internet and attached bundle remain as configured. This cell replaces only the worker; the tunnel URL/key stay the same. Cached Base loading happens once and can take a few minutes; it is separate from generation time.
3. Return the final status, expected **`READY_FOR_NAILS_LATENCY_COMPARE`**, and advertised choices `[8, 12, 20]`. A fallback status **`ORIGINAL_20_STEP_WORKER_RESTORED`** means no faster worker is available; return the named update log/evidence rather than changing models.
4. After readiness, Codex will benchmark the same hand/style at 12 and 8 through the central application handler. Preserve output PNGs, step/provenance metadata and timing; compare with the saved 20-step output and check zero out-of-mask edits. Inspect polish/material differences; no invented numerical acceptance tolerance. Choose the faster acceptable setting based on observed results and restart the backend with that value.

**At preparation time the setting remained 20.** The later live comparison and current local setting follow below. Renderer-only styles need no GPU and remain unchanged. Original three services and 20-step inference are rollback. Full same-session Gate 3 acceptance remains separate work.

## Returned update failure and correction

Supervisor returned the 09:00:41 Kaggle update report and worker log. The candidate failed **during import, before Base initialization**, because the isolated tree omitted `data/makeup/DATA-M001-paired/inference_presets.json`. This is a packaging bug, not a model, adapter, dependency or GPU inference failure. The original worker was restored, ready with one Base and the same feature routes; faster inference did not run. [Reviewed report and artifact hashes](nails-latency-update-failure-20260928.json).

The controller now copies only the existing approved preset JSON alongside the small source tree. Before stopping anything, it imports the actual assembled server in a fresh process and confirms zero Base loads plus advertised 8/12/20 choices. Failed preflight preserves the current worker and writes `PREFLIGHT_FAILED_ORIGINAL_WORKER_UNCHANGED` with its diagnostic log. Existing startup rollback remains. Real import regression reproduces the missing-file failure and passes with the preset included; a separate test proves failed preflight cannot stop the current worker. Final focused tests: **43 passed**; one existing multipart warning. No application, models or generation settings changed in this correction.

The Supervisor retried the regenerated cell in the same notebook. Returned report/log confirm corrected startup, with source hashes matching the committed candidate, one loaded Base and supported 8/12/20 choices. Startup was 51.015 seconds, including 35.354 seconds Base/first adapter loading; no dependency setup/download or tunnel change. [Reviewed worker evidence](nails-latency-worker-review-20260928.json).

## Actual central API and GPU comparison

Both candidates used the same original hand and `classic_red`, real HTTP `POST /features/nails/generate` on the running local FastAPI, the existing hybrid localization/segmentation/refinement/crops/compositor, and the same running updated Kaggle server. Backend was restarted for each configured step count; no notebook restart or Base rebuild between candidates. The previous 20-step full-hand result was retained as reference, not generated again. These are single observations, not statistical timings; local pipeline initialization and network/CPU costs are included in wall time, but worker startup is separate.

| Steps | Full-hand wall seconds | Model generation seconds | Saving against 20 |
| --- | --- | --- | --- |
| 20, saved reference | 365.375 | 322.810 | baseline |
| 12 | 264.062 | 226.060 | 27.728% |
| 8, selected | 221.000 | 185.100 | 39.514% |

Both candidates returned HTTP 200, five edited nails, the approved adapter/Base hashes and correct actual step metadata. Five crop records per candidate verify provenance. The worker stayed ready with foundation load count one throughout. Independent comparison with the saved final refined mask finds **zero changed pixels outside nails** for both results. Compared with 20, 12 differs on 6,778 pixels (mean absolute channel difference inside nails 0.966, maximum 12); 8 differs on 7,247 pixels (mean 2.206, maximum 21). Exact equality is not claimed and no numerical acceptance tolerance was invented. Visual inspection at original resolution finds recognizable glossy red material and highlights on all five nails, with small color/highlight differences and no evident material regression on this photo. Private outputs remain ignored in `.tmp/nails-upload-diagnosis/`.

Current ignored local `backend/.env` contains `NAILS_INFERENCE_STEPS=8`; the running backend's successful 8-step response confirms it is active. **Code default stays 20** to preserve approved references and separate-runtime compatibility. Set 12 or 20 and restart FastAPI for alternatives. A fresh original v2 notebook needs the update cell before 8 is accepted; otherwise use 20. Hair/Makeup settings, models/adapters, seed, guidance, crop dimensions, renderer paths and UI are unchanged. All private assets, URLs and keys remain outside Git.

[Numeric, provenance and memory evidence](nails-latency-live-review-20260928.json) records all ten actual crop completions. Whole-device readings there are post-inference samples, not claimed peak VRAM. No OOM occurred. One actual `nude_pink` central request after the selection also completed through the local renderer with **zero added remote requests**; its evidence is included in that review. Prior 43 focused and 11 frontend client tests cover the implementation; no additional code change or unrelated suite rerun was required for live configuration/evidence.

Limits: one hand and Classic Red, one run per candidate. Glossy Black quality at reduced steps and other poses remain unreviewed; no universal quality/latency promise or full Gate 3/browser acceptance claim. Next: use the 8-step current app, review more user-selected examples when needed, and finish the separate remaining Gate 3 browser/cross-feature acceptance. Further latency work should target measured repeated crop overhead without changing the proven image boundary or model behavior.
