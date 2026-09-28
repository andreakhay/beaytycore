# Capstone with TRAIN-002 Hair styles

This new candidate adds the existing TRAIN-002 adapter to the unified worker. No training, prompt, model setting, Nails change or second foundation. Local artifact and mocked routing checks passed. Live unified TRAIN-002 inference still needs verification.

## One time Kaggle setup

1. Upload `F:\HAIR\artifacts\capstone_train002_20260928_v1.bin` as a private Kaggle Dataset. Keep the original Deployment-01 Dataset as rollback. You may attach both, but there must be exactly one copy of the new file in notebook inputs.
2. Import `F:\HAIR\notebooks\capstone_start_train002.ipynb` as a separate private notebook. Attach the new Dataset, select T4 and Internet, and enable the same `AI_REMOTE_API_KEY` and optional `HF_TOKEN` Secrets.
3. Finish any active generation, then stop the old Kaggle session manually. Start a fresh session for this new notebook. Do not paste the expanded cell into the old running worker session. It will refuse to overwrite the old extracted package.

Package: 171,360,891 bytes. SHA-256 `f0d1fed52e00b6c5a1da2cade3731237675cdebbfc0b2cde3b2dbda99a4019ac`. Upload once, not every session. Do not commit or publicly share the package; it retains private validation assets.

## Normal startup

1. Run **START CAPSTONE** in the configured expanded notebook. The same complete cell is available in `F:\HAIR\notebooks\START_CAPSTONE_TRAIN002_cell.py`.
2. Wait for **CAPSTONE_AI_READY**.
3. Double-click `F:\HAIR\START_CAPSTONE.bat`. Wait for **CAPSTONE READY**.
4. Reload the Hair page at http://localhost:3000. The signed discovered bundle identity selects the thirteen-style registry automatically. No URL copying or `.env` change.

## Minimum live check

Generate Bun once from the approved portrait. Confirm Hair result metadata says `adapter_id=train002`, the approved hash and 500 training steps. Then generate Crew Cut to check restoration to `train001` without a second Base. Continue the deployment rehearsal with Makeup, model Nails and renderer Nails. Keep outputs and return the notebook's **COLLECT REHEARSAL EVIDENCE** ZIP plus the local safe diagnostics. Do not repeatedly retry a failure. No exhaustive ten-style quality claim is intended.

The historical TRAIN-002 adapter smoke was live tested on an earlier Hair runtime. This new unified deployment candidate has only local and mocked evidence until the new run is returned.

## Rollback and recovery

Open the original configured `capstone_start.ipynb` with the original Deployment-01 bundle in a fresh session. Its publication selects the original three Hair styles, plus unchanged Makeup and Nails. The local legacy TRAIN-002 registry remains in `.env` for the separate original Hair runtime; the capstone launcher overrides it only in its own process environment.

If discovery is unavailable, explicitly use the current expanded worker URL with `START_CAPSTONE.bat --url <current HTTPS URL> --train002`. The default manual override selects the original three-style bundle. Never use the expanded override against the old worker.
