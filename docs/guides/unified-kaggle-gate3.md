# Gate 3 live acceptance handoff

2026-09-28. **READY FOR LIVE ACCEPTANCE after local checks; not yet passed on Kaggle.** This starts one new temporary GPU service. Leave all old Hair, Makeup and Nails notebooks/bundles intact as rollback.

## 1. Kaggle setup

1. Create a **new private** Kaggle notebook. Select **Tesla T4 GPU** and enable **Internet**. Use the exact Python/Torch/CUDA host shown in Gate 2; setup refuses a different host instead of claiming comparable results.
2. Upload [unified_gate3_20260928_v2.bin](../../artifacts/unified_gate3_20260928_v2.bin) as a **private** Kaggle Dataset and attach it as notebook input. File size **128,958,525 bytes**; SHA-256 `a3d73ce4ac0995a17bfa6a7c48253e2a2fa7db9ae635941295804d60dcb03683`. It contains all three approved adapters; no other private model Dataset is needed for the default three Hair styles.
3. In Kaggle **Add-ons → Secrets**, create/enable **`AI_REMOTE_API_KEY`** with a random value of at least 24 characters. For example, generate a value locally with `python -c "import secrets; print(secrets.token_urlsafe(32))"`; save that value privately for `backend/.env`. Do not paste the value into a notebook cell or screenshot. If the pinned Base download requires Hugging Face authentication, also enable the existing optional **`HF_TOKEN`** Secret.
4. Import [unified_gate3_kaggle.ipynb](../../notebooks/unified_gate3_kaggle.ipynb). Run **Cells 1, 2, 3 in order**. Cell 1 verifies/extracts the exact bundle. Cell 2 installs the reviewed environment, downloads one Base snapshot, loads one foundation/first adapter, starts one Uvicorn worker and one Cloudflare Quick Tunnel. Cell 3 prints **ONE URL**, public readiness and a setup evidence ZIP. Keep this notebook running while the application is used. Setup may take several minutes. A `READY_FOR_LIVE_ACCEPTANCE` startup status is not a Gate 3 pass.

If Cell 2 fails, inspect `/kaggle/working/unified_gate3/startup.json` and the named stage log. A changed Kaggle environment or unavailable tunnel is a concrete blocker; do not change model settings to bypass it. The new service refuses to replace a process on its port. The temporary Quick Tunnel URL expires with the session.

## 2. Configure the existing application

In the ignored `F:/HAIR/backend/.env`, set these values and keep any existing local Nails landmark/segmentation paths:

```dotenv
GENERATION_ENGINE=remote_flux
MAKEUP_GENERATION_ENGINE=remote_makeup
NAILS_PREVIEW_MODE=hybrid
AI_REMOTE_URL=https://<the one URL printed by Cell 3>
AI_REMOTE_API_KEY=<the exact value in your Kaggle AI_REMOTE_API_KEY Secret>
```

The three existing feature-specific URL/key pairs can stay in `.env`, but the complete `AI_REMOTE_*` pair takes precedence. Do not put the API key in frontend environment variables. Restart the local backend after editing `.env`; the Nails pipeline caches its client at process startup. Start the existing backend and frontend using the [README commands](../../README.md). The frontend continues using `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`; no page or UI changes are required.

The unified server URLs are:

| Route | Responsibility |
| --- | --- |
| `GET <one URL>/health` | Public process/Base/readiness and active feature; does not show the key |
| `GET <one URL>/status` | Protected safe request/provenance/memory history; `X-API-Key` required |
| `POST <one URL>/hairstyle/generate` | Existing Hair multipart contract |
| `POST <one URL>/makeup/generate` | Existing Makeup multipart contract |
| `POST <one URL>/nails/generate` | Existing localized Nails crop multipart contract |

The local browser does **not** call Kaggle directly. Local FastAPI still handles uploads, feature dispatch and all Nails localization/segmentation/compositing. The renderer-only Nails styles do not call the GPU.

## 3. Live acceptance sequence

Use approved, non-private images where available. In one running Kaggle session, use the actual pages at `http://127.0.0.1:3000`:

1. Hairstyle page: generate `crew_cut`; record the central API HTTP status, style and result metadata.
2. Makeup page: generate `natural_makeup`; record the same.
3. Nails page: generate `classic_red` from an approved hand image. This hybrid path may request five sequential crops and take several minutes. Record central response `inference_path=model`, adapter ID/hash, nail count and timing. Do not move the local vision stages into Kaggle.
4. Hairstyle page: generate `crew_cut` again. This proves restoration after Hair → Makeup → Nails → Hair.
5. Nails page: generate `nude_pink`. Confirm central response `inference_path=renderer`. Cell 4 below should show **no new Nails GPU request** for this renderer-only step.

After these requests, return to the same notebook and run **Cell 4 once**. It sends four harmless local HTTP error probes (wrong key, unknown feature, invalid style, invalid image), checks that they did not generate an image or make the runtime unready, then reads protected `/status` using the Kaggle Secret without printing the key. It records Base load count, per-request feature/style/adapter/HTTP status and switch count, and creates `/kaggle/working/unified_gate3/live-evidence.zip`. Download and attach that ZIP plus the non-private browser/central API status summary. The protected report records per-crop Nails calls, so five crop records for one full hand are expected. Do not commit the ZIP, generated portraits, the key or the temporary tunnel URL to Git.

If any request fails, record which stage and HTTP status, keep the session running and return the evidence. Do not claim Gate 3 passed from startup health alone.

## Rollback

Remove **both** `AI_REMOTE_URL` and `AI_REMOTE_API_KEY` from `backend/.env`, restore the existing `FLUX_REMOTE_*`, `MAKEUP_REMOTE_*` and `NAILS_REMOTE_*` settings and restart FastAPI. The separate GPU servers, original runtime code and legacy backend routes are unchanged. There is no silent automatic fallback during unified mode.
