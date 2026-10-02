# Single folder BeautyCore and AI integration

**Decision:** CONFIRMED for a staged, additive import on `codex/unified-beautycore`.
**Evidence:** repository inspection on 2026-10-02. BeautyCore source commit `351c0d8ca43c384117b13630fb05fa3cd248229c`; HAIR source commit `4f215fb1332d4f72b840cd83b9a4de18097fed63`.
**Progress:** IN PROGRESS; source import and local contracts VERIFIED. Live Client plus Kaggle acceptance and private client handoff remain NEEDS VERIFICATION.

## Why this direction

The existing BeautyCore client, stylist, and admin application is a Next.js app with Neon, cookie sessions, and its own API routes. The working AI application is a Python FastAPI backend plus an older Next.js frontend. BeautyCore already has a tested Client Consultation page and a server only `/api/ai/*` adapter to the FastAPI contracts. Keeping that boundary preserves database ownership, authorization, consultation validation, and the original AI pipelines. The current BeautyCore launcher still imports `F:\HAIR` and lives on `I:`, so it does not meet the one folder handoff requirement.

Use the HAIR repository as the integration root because it holds the verified backend, Nails CPU assets, model contracts, Kaggle notebook, signed discovery, and fallback runtimes. Import the **tracked BeautyCore source snapshot** under `beautycore/` without copying `.git`, `.env.local`, `env.local`, `node_modules`, `.next`, logs, generated images, or runtime state. Leave the original `I:` checkout untouched. Its commit remains recoverable under annotated tag `beautycore-phase3-pre-unified-import-2026-10-02`; HAIR remains recoverable under branch/tag `baseline/hair-ai-pre-beautycore-import-2026-10-02` / `hair-ai-pre-beautycore-import-2026-10-02`.

## Final local shape

```text
BeautyCore unified root (currently F:\HAIR)
  beautycore/       existing BeautyCore Next.js UI, auth, roles, Neon, API adapter
  backend/          existing FastAPI Consultation and Hair/Makeup/Nails handlers
  data/             existing local AI configuration and private Nails CPU assets
  scripts/          existing Kaggle discovery and unified runtime support
  notebooks/        existing private Kaggle startup workflow
  START.bat         one local launcher for FastAPI and BeautyCore
  STOP.bat          stops only launcher owned local processes
  frontend/         preserved old HAIR UI for rollback, never opened normally
```

This is one **local project folder and one user facing BeautyCore application**. FastAPI remains a private local process because Nails CPU processing, Python model dependencies, and the proven dispatcher live there. The existing Kaggle notebook remains the external GPU service for the capstone, as the Supervisor confirmed. A single process or fully offline GPU installation is not claimed.

## Actual boundaries and conflicts

- Browser to BeautyCore uses the existing HTTP only cookie. BeautyCore rereads the current Neon user and requires `client` for the adapter. BeautyCore to FastAPI stays on loopback; neither browser nor Kaggle receives the BeautyCore cookie.
- FastAPI continues to own Gemini Consultation state, recommendation validation, Hair/Makeup/Nails generation, and Nails local hybrid processing. BeautyCore owns users, roles, appointments, pricing, inventory, and the old Advisor. No schema merge or migration is required for this import.
- The two Next.js projects have different locked React/Next versions. Keep separate package manifests and `node_modules`; only BeautyCore is started. Node's Google SDK and Python's `google-genai` do not share an environment. Nails segmentation keeps its isolated Python environment.
- BeautyCore's current launcher has an absolute default `HAIR_ROOT=F:\HAIR`, and the prior runbook refers to two drives. Replace those assumptions with paths derived from the unified root. Keep signed discovery, private process environment injection, worker checks, the read only adapter probe, and Windows job ownership.
- The FastAPI backend loads `backend/.env` locally; BeautyCore loads `beautycore/.env.local`. Both remain ignored and server only. Model backed Nails also needs the local MediaPipe and segmentation artifacts under `data/nails/`; those are private, ignored, and must be packaged separately for a client handoff. The Base/LoRAs remain in the approved private Kaggle bundle, not Git.
- Consultation state/photos/results are process local and expire. Copying source does not turn them into persisted records. BeautyCore service prices and booking remain authoritative.

## Staged implementation and gates

1. **Source import:** copy only tracked BeautyCore files to `beautycore/`; compare file hashes with the protected source commit. No AI or BeautyCore behavior changes.
2. **Relative launcher:** add root `START.bat` and `STOP.bat`; make the imported launcher resolve `backend/`, `beautycore/`, and scripts from its parent root. Stop launching the old HAIR frontend. Preserve fail closed worker discovery, adapter transport, and process ownership. Test relocation and startup failure paths with mocks.
3. **Local dependency and configuration contract:** use `beautycore/package-lock.json` and `backend/requirements.txt`; keep per runtime environments. The launcher checks the three private Nails assets under the unified root, and the one folder installation guide lists them. Do not copy secrets or model weights into Git. This contract is locally VERIFIED.
4. **Local integration gate:** typecheck/build BeautyCore, run its adapter/client tests and FastAPI tests relevant to the import, then prove one BeautyCore to FastAPI mocked request without GPU. This gate is VERIFIED; see [local evidence](../experiments/unified-beautycore-local.md).
5. **Live gate and handoff:** use the existing Kaggle worker, then the root launcher, Client login, Gemini consultation, sequential generation, Select, Custom, and post run readiness. Only after returned live evidence may a final client handoff package and baseline be declared ready.

## Protected components

Do not edit BeautyCore authentication, role checks, Neon schema, appointments, inventory, old Advisor, or existing Client AI behavior for the source import. Do not edit FastAPI generation, Gemini provider, catalogs, validator, Nails hybrid pipeline, FLUX/LoRA settings, GPU ownership, or Kaggle runtime. Preserve separate original GPU runtimes and the old HAIR frontend as rollback until the unified folder passes its own gate.

## Known limits

The signed Kaggle tunnel and manual `START CAPSTONE` cell remain necessary. A client delivery needs an approved way to supply the ignored private Nails CPU assets and Kaggle bundle/Secrets; Git source alone is not a complete install. No live integrated acceptance or portability to another drive is verified by this plan.
