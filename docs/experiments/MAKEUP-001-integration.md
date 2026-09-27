# MAKEUP-001 application integration

Recorded 2026-09-26. Status: local implementation VERIFIED; live Kaggle request NEEDS VERIFICATION.

## Approved boundary

The Project Lead approved both held-out Original / Base / MAKEUP-001 comparison sheets. This implementation connects that checkpoint through a separate Makeup service. It retains all ten fixed inference presets. It does not retrain, use closed dataset experiments, or change Hair runtime, registry, adapter switching, prompts, or UI.

MAKEUP-001 is a general Makeup edit LoRA, not ten trained FFHQ style classes. Identity details, skin texture, lighting and skin tone can change. Natural and No-Makeup can be heavier than their names imply. The visual approval does not establish population generalization or exact facial geometry preservation.

## Implemented request path

`/makeup` sends the portrait and selected Makeup style to the existing local FastAPI API. A separate `RemoteMakeupEngine` normalizes the image to 512 by 512 and forwards it to an authenticated Makeup GPU service. That service loads only the approved MAKEUP-001 adapter once. It does not import the Hair registry or switch adapters. It maps the preset ID to the exact reviewed prompt and returns the generated PNG with model and adapter provenance.

Local settings are `MAKEUP_GENERATION_ENGINE=remote_makeup`, `MAKEUP_REMOTE_URL`, and `MAKEUP_REMOTE_API_KEY`. The Kaggle Secret is `MAKEUP001_API_KEY`, with a random value of at least 24 characters. Hair settings are independent and unchanged. Default Makeup mode remains an explicitly labeled mock. A configured remote failure returns a visible error, not a mock fallback. `/makeup/health` describes local configuration only; the GPU service `/health` is the separate model load check.

The local client validates the returned model revision, adapter ID/hash, preset hash, style, feature, LoRA-active flag, generator, image type and dimensions. GPU requests are limited to one in flight. Uploads are processed in memory and are not saved by this service.

The Makeup page now labels real results and mock previews distinctly, reports errors and locks source/style changes while generating. The existing three-link header overflow at a 390-pixel viewport was corrected with wrapping on the Makeup page only. No shared layout refactor was required.

## Frozen runtime artifacts

| Item | Value |
| --- | --- |
| Model | `black-forest-labs/FLUX.2-klein-base-4B` |
| Revision | `a3b4f4849157f664bdbc776fd7453c2783562f4d` |
| Adapter | `MAKEUP-001`, 46,223,600 bytes |
| Adapter SHA256 | `f6f0419e4259a75102f08a450222ad806e3aec1c2ae50ff89f875139084ae510` |
| Preset SHA256 | `8e6e244f6174dc70f33cb15a037f5e67e2a245f15278967f4d2f85bc909cd5f5` |
| Inference | FP16, CPU offload on GPU 0, 512 by 512, 20 steps, guidance 4.0, seed 1977 |
| Bundle | `F:/HAIR/artifacts/makeup001_kaggle_runtime.zip` |
| Bundle bytes | 42,409,912 |
| Bundle SHA256 | `1faebd79b027f64a56d1a70ec0046ae92d528998f4f3964921245f6b0a23ec5b` |

`scripts/package_makeup001_runtime.py` verified the supplied training/evaluation ZIP before packaging. The bundle includes the final adapter, model/preset contract, exact presets, independent service/bootstrap, inference requirements, and training evidence. It excludes portraits, optimizer state, training entry points and Hair adapters. The ZIP and its code inventory/adapter checks passed after extraction to a CPU-only verification directory. This is not a GPU load result.

Reproduction command from the repository root, using a new output filename to preserve the existing bundle:

```powershell
python scripts/package_makeup001_runtime.py --archive C:/Users/Gigabyte/Downloads/makeup001_250_with_evaluation.zip --output artifacts/makeup001_runtime_rebuild.zip
```

The full notebook cells and local configuration steps are in [the live demo guide](../guides/makeup001-live-demo.md). Use a new private notebook and Dataset. The bootstrap stages dependency installation, pinned model download, server load and tunnel readiness with observable logs. It includes the text encoder generation config in the required download patterns. It constrains installation to the existing Kaggle Torch build.

## Local verification

The Project Lead approved running the repository's existing test tools. Results:

| Command | Result |
| --- | --- |
| `python -m pytest tests -q`, in `backend` | 100 passed; one existing python_multipart deprecation warning |
| `npm run lint`, in `frontend` | passed |
| `npm run build`, in `frontend` | passed |
| `npm run test:e2e -- --reporter=line`, in `frontend` | 11 passed |
| `git diff --check` | passed |

API tests cover independent engine selection, exact presets, invalid response provenance, authentication, concurrent request exclusion, failures, image validation and bundle integrity. Playwright covers the existing Hair flows, Makeup mock flow, mocked real Makeup result, loading/error recovery, and narrow-screen behavior. Test network responses do not prove real GPU inference. The complete suite also includes the existing Nails tests; no Nails implementation change was made for this task.

Local screenshots: `F:/HAIR/.tmp/makeup001_mobile_after.png` and `F:/HAIR/.tmp/makeup001_desktop_after.png`. The 390-pixel mobile page has scroll width 390 after the fix. They show the local mock state, not a real model result.

## Kaggle load gate, Project Lead report

The first Kaggle bootstrap exited at secret retrieval with `No user secrets exist ... MAKEUP001_API_KEY`, before model download or load. After the Project Lead attached the secret and retried, the supplied log shows all five pipeline components loaded in 39.9 seconds, Uvicorn running on port 8766, local and tunnel `/health` returning 200, and a reported `health.json` with `status: ready`, `feature: makeup`, `lora_active: true`, `adapter_steps: 250`, all ten style IDs, and the pinned model revision, adapter hash and preset hash listed above. The reported temporary URL is `https://commissioner-utils-mid-gene.trycloudflare.com`. This verifies the reported model load and public health response, not a generated image or end to end browser request. The log and health were supplied in chat; no new Kaggle artifact ZIP was downloaded for independent audit. The API key was not disclosed.

## Remaining live gate

The Project Lead's Kaggle load gate passed. No live model generation was reported, no local private key/URL was configured by Codex, and no existing Hair session was manipulated. Set only the Makeup environment variables in the local backend and restart it. Then verify a browser request with a user portrait, all returned provenance, loading/errors, and the visible result. Keep the inference session running during the demo. Save the request observations without exposing the private key. Do not mark end to end Makeup inference VERIFIED before this check.

## First browser request failure and targeted V2 repair

The Project Lead's first `/makeup` browser generation reached the public Makeup GPU service but returned HTTP 500. The supplied `server.log` traceback identifies `torch.cuda.reset_peak_memory_stats(0)` raising `RuntimeError: Invalid device argument` in `MakeupRuntime.generate`, before the FLUX pipeline call. This is an optional telemetry failure, not evidence that model generation itself failed. The same session's `/health` had passed, but the first image was never generated.

`scripts/makeup_inference_server.py` now treats both peak memory reset and reading as optional. A failed statistic is logged or recorded as `peak_gpu_mib: null` without stopping image generation. No model, checkpoint, prompt, seed, step count or Hair code changed. A CPU regression test reproduced the exact exception before the patch and passed after it. Full backend suite: 101 passed, one existing deprecation warning.

The corrected private bundle is `F:/HAIR/artifacts/makeup001_kaggle_runtime_v2.zip`, 42,409,973 bytes, SHA256 `cf9625999b7c107f7c40c3aeb4412bbb1d787f90209868e9c357936b90e9140a`. The final adapter hash remains `f6f0419e4259a75102f08a450222ad806e3aec1c2ae50ff89f875139084ae510`. The updated [live guide](../guides/makeup001-live-demo.md) locates V2 specifically and provides a guarded same-session Makeup-only restart. A successful V2 GPU image request and visual review remain NEEDS VERIFICATION.
