# NAILS-001 hybrid live verification handoff — 2026-09-27

**Status: NEEDS VERIFICATION.** The Supervisor chose to run Kaggle personally. No authenticated Kaggle GPU session was available in this agent's browser (Kaggle displayed Sign In), and no local Kaggle CLI credentials were present. No GPU service was launched and no real Red/Black application request was made in this task. Do not interpret this handoff as live model approval.

## Verified before handoff

- Private runtime bundle: `data/nails/work/NAILS-001-LOCAL-v1-runtime-v2.bin`, 42,214,993 bytes, SHA-256 `adf324b0e2bcf6f23f34641c6448b8874898e4b910750c7cc8fe9c002f072699`; ZIP CRC passed with eight members.
- Bundled immutable step-50 adapter: `adapter/nails001_local_v1.safetensors`, SHA-256 `5bff16c67e0014c78a6d938813347685f914f8a608d76407b10f5b54b7a0eb1f`, matching the manifest and runtime contract.
- The selected real hand IDs `0000000` and held-out `0000088` each passed the current MediaPipe/isolated YOLO mask validation with five visible nail components. This only verifies input suitability locally.
- `python -m pytest tests -q` from `backend` passed **110 tests** (one third-party deprecation warning). `python -m py_compile` passed for changed Python files. The live smoke CLI `--help` starts successfully.

## Added diagnostic instrumentation

The existing `/nails/generate` behavior now returns `metadata.timing_seconds` for image validation, normalization, hand localization, nail segmentation, mask/crop preparation, GPU request, server-reported model generation, result reconstruction, compositing, and total handler time. `model_generation` is inside `gpu_request`; those values must not be summed. `scripts/nails001_live_smoke.py` calls the application API for Red/Black on both hands and all three renderer styles on Hand A, saves output images, a review sheet and a timing report, and verifies unchanged pixels outside a freshly computed nail mask. It also checks invalid-image rejection. It does not bypass the API or change model settings.

## Required run and review

Follow `docs/guides/nails001-hybrid-live-demo.md` with the verified bundle. Keep the Kaggle notebook alive while running the backend and smoke script. Return `data/nails/work/live-smoke/report.json`, `review-sheet.png`, and the seven full-size style result PNGs for visual review, plus Kaggle `health.json`, `environment.json`, and a copy of the server log if a request fails. Do not share `NAILS001_API_KEY` or `backend/.env`.

Only after the real four model requests can we report actual Red/Black generation time, decide whether latency warrants batching or fewer inference steps, and classify demo readiness. No batching or step-count change was made here.

## Supervisor Kaggle launch report

The Supervisor's first launch reached `VERIFYING_BUNDLE`, then `FAILED` at `UserSecretsClient().get_secret("NAILS001_API_KEY")`. Kaggle reported: `No user secrets exist for kernel id 135983099 and label NAILS001_API_KEY.` No dependency check, server log, endpoint, or health result was written. This is an unattached/missing notebook Secret, not a checkpoint, model-load, CUDA, or inference failure. The guide now requires a no-print Secret preflight and provides a retry cell that keeps the first `launcher.log`. Live model verification remains pending.

## Successful model load and partial real application evidence

The Supervisor's retry reported `READY` with Kaggle T4/CUDA 12.8, Torch `2.10.0+cu128`, Diffusers `0.39.0.dev0`, Transformers `5.5.3`, pinned Base revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, active step-50 adapter hash `5bff16c67e0014c78a6d938813347685f914f8a608d76407b10f5b54b7a0eb1f`, and 52.98 seconds model load. A direct public `/health` check also returned `200 OK` with matching metadata. No training occurred.

The downloaded `NAILS-001-live-review-20260927-191106.zip` (522,617 bytes, SHA-256 `2120e0f808bfdf9654b97abed54316ef7f22c56a3ef038f13fbac6bc11bb0c82`) passed ZIP CRC and all five result hashes in `report.json`. It is **partial**: Hand A has Red, Nude, Black, French and Ombre, but Hand B has no results; the final review sheet, mask QA records and invalid-image result are absent. The ZIP must not be called a complete two-hand smoke test.

Hand A Red and Black both used `inference_path=model`, reported five nails and the approved adapter hash via the strict remote client. Visual inspection found recognizable Red and Black on all five nails, with correct apparent nail alignment and unchanged surrounding hand. Their application wall times were 378.969 and 382.375 seconds, respectively. GPU request accounted for 366.812 and 375.609 seconds; server-reported generation accounted for 355.69 and 365.18 seconds. Segmenting the hand took 5.812 and 6.328 seconds. The three renderer styles were visually recognizable and took 5.813–6.578 seconds end to end. An independent rerun of the local mask detector found **zero changed pixels outside the nail mask** for all five Hand A outputs.

At roughly 6.3 minutes per Red/Black hand, current latency is too high for a practical demo. Inspection of the pinned Diffusers `Flux2KleinPipeline` implementation found that a list of input images becomes multiple conditioning references shared with every batch output, so its public `image=[crop1,...]` API does not preserve one-to-one nail correspondence. This rules out a safe direct five-crop batch using that API; no production batching change was made. Complete the held-out Hand B baseline first, then compare bounded 12-step and, if useful, 8-step inference to the evaluated 20-step setting. No reduced-step output exists yet.

`scripts/nails001_live_smoke.py --resume` now verifies existing saved result hashes and skips the five Hand A calls. It runs only Hand B Red/Black, invalid-image handling, final mask pixel QA and review sheet generation. A dry run with an intentionally unreachable local port confirmed all five Hand A results were skipped before the missing Hand B request failed; no GPU call or result overwrite occurred in that dry run.

After local `.env` was set to live hybrid mode, a placeholder Nails test failed because it inherited that setting. `backend/tests/conftest.py` now pins `NAILS_PREVIEW_MODE=mock` for the test suite, matching its existing Hair/Makeup isolation. Production configuration was not changed. `python -m pytest tests -q` from `backend` then passed **110 tests** (one third-party deprecation warning).
