# Unified BeautyCore local integration evidence

**Date:** 2026-10-02. **Status:** LOCAL VERIFIED for source import and contracts; LIVE ACCEPTANCE PENDING.

- Source checkpoints: HAIR `4f215fb1332d4f72b840cd83b9a4de18097fed63` protected by `baseline/hair-ai-pre-beautycore-import-2026-10-02` and matching annotated tag; BeautyCore `351c0d8ca43c384117b13630fb05fa3cd248229c` protected by annotated tag in its unchanged `I:` repository.
- Imported exactly 150 Git tracked BeautyCore files from the protected commit into `F:\HAIR\beautycore/`; each imported byte sequence was SHA-256 checked against the source commit. No untracked source file, `.env`, model, generated output, or dependency directory was copied in that source import.
- An ignored BeautyCore `.env.local` was separately copied into the unified checkout for local configuration. It is not staged or committed. The three existing private Nails runtime assets remain ignored under the unified root. Launcher code derives the root from its own path and overrides old absolute Nails paths in process memory.
- `python -m pytest tests -q` from `backend/`: **408 passed**, 1 existing `python_multipart` warning. An earlier invocation from the repository root failed test collection because `app` was not on Python's import path; rerunning from the backend's required working directory passed.
- `python -B -m unittest discover -s tests -p test_capstone_launcher.py -v` from `beautycore/`: **12 passed** in the installed dependency environment, including a read only adapter request to fake private FastAPI and fail closed missing Nails asset handling. A sandboxed attempt failed the Node spawn with `EPERM`; the same tests passed under the permitted Windows process context.
- `node node_modules/tsx/dist/cli.mjs --test tests/ai-adapter.test.ts tests/ai-client-flow.test.ts`: **23 passed**. `npm run typecheck`: passed. `npm run build`: passed, including the Client, Stylist, Admin, Advisor, Consultation, and AI adapter routes.
- `npm ci --offline --no-audit --no-fund` in the unified `beautycore/` completed and installed 562 locked packages. A first sandboxed install failed with Windows `EPERM`; the approved retry using the populated cache completed. No lockfile modification.
- No live Kaggle worker, Gemini conversation, real generation, Neon booking, or final Client walkthrough was performed in this local integration step.
- Staged whitespace check reports two trailing spaces in the imported legacy `test3.mjs`; they exist in the protected BeautyCore source and were preserved byte for byte. No new launcher or integration file has a whitespace finding.

The original `I:` BeautyCore checkout and old HAIR `frontend/` remain unchanged. Live acceptance must use root `START.bat` after a current signed Kaggle publication, not the old HAIR frontend launcher.
