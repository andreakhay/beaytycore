# Nails latency comparison

2026-09-28. **Preparation DONE; LOCAL/MOCKED VERIFIED; faster GPU results NEEDS VERIFICATION.** Supervisor authorized comparing 12 and 8 inference steps against the current 20-step result before selecting a faster setting. This is a bounded inference experiment, not retraining or a Gate 3 pass.

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

**Current setting remains 20.** No faster result, speedup or quality approval is claimed. Renderer-only styles need no GPU and remain unchanged. Original three services and 20-step inference are rollback. Full same-session Gate 3 acceptance remains separate work.

## Returned update failure and correction

Supervisor returned the 09:00:41 Kaggle update report and worker log. The candidate failed **during import, before Base initialization**, because the isolated tree omitted `data/makeup/DATA-M001-paired/inference_presets.json`. This is a packaging bug, not a model, adapter, dependency or GPU inference failure. The original worker was restored, ready with one Base and the same feature routes; faster inference did not run. [Reviewed report and artifact hashes](nails-latency-update-failure-20260928.json).

The controller now copies only the existing approved preset JSON alongside the small source tree. Before stopping anything, it imports the actual assembled server in a fresh process and confirms zero Base loads plus advertised 8/12/20 choices. Failed preflight preserves the current worker and writes `PREFLIGHT_FAILED_ORIGINAL_WORKER_UNCHANGED` with its diagnostic log. Existing startup rollback remains. Real import regression reproduces the missing-file failure and passes with the preset included; a separate test proves failed preflight cannot stop the current worker. Final focused tests: **43 passed**; one existing multipart warning. No application, models or generation settings changed in this correction.

Retry: reopen the regenerated `F:\HAIR\notebooks\nails_latency_update_cell.py`, replace the previous update cell contents with the entire current file, and run that cell once while no generation is active. Keep the running notebook, existing input/Secret and URL; do not rerun setup. Expected `WORKER_IMPORT_PREFLIGHT_PASSED` is captured in the preflight log; final status remains `READY_FOR_NAILS_LATENCY_COMPARE`. Actual corrected Kaggle startup and 12/8 generation remain **NEEDS VERIFICATION**.
