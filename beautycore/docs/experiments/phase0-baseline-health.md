# BeautyCore Phase 0 baseline health, 2026-10-02

Baseline source commit: `dbd0b06bfdc0bdaadf2bbed048f369e8dc3b45a6`.
Annotated tag: `beautycore-pre-ai-integration-baseline-2026-10-02`.
No remote configured or push performed. The existing source was checkpointed after replacing the populated SESSION_SECRET in .env.local.example with an explicit placeholder. No runtime configuration or application behavior changed. The local env.local file remained ignored and uncommitted. Staged source had no detected API keys, private-key blocks, credentialed URLs, model weights, notebook outputs, or generated artifacts. Two legacy test script lines have preexisting trailing whitespace.

## Checks

- The original I: checkout had no node_modules. Two npm ci attempts (normal and offline) stalled while populating directories without installing command binaries; both were stopped. Cause UNKNOWN. Its direct npm run typecheck and npm run build consequently reported missing tsc and next.
- A clean temporary extraction of the baseline commit completed `npm ci --offline --no-audit --no-fund --ignore-scripts`: 562 packages in 31 seconds. The test copy contained source only, no local env or private photos.
- In that clean copy, `npm run typecheck` passed.
- `npm run build` first compiled and typechecked but stopped while collecting route data because DATABASE_URL was absent. With a nonfunctional process-only placeholder database URL, an offline run could not fetch existing Google fonts. An allowed-network run with the same placeholder URL completed the production build and generated 40 routes. No live Neon query or app runtime smoke test was performed.
- `npm run lint` failed before linting because the package script invokes `next lint`, which Next.js 16 interprets as a missing project directory. `npx --no-install eslint .` also failed before linting because eslint.config.js imports eslint-plugin-react-refresh, absent from package.json and the lockfile. These are preexisting tooling defects; Phase 0 did not change them.
- No `test` package script exists. The named scripts/test-analyze.ts and scripts/test-preview.ts use external AI providers, so they were not run in this baseline check.

## Meaning

Source typecheck and production compilation passed under a clean dependency install. The build did not verify the actual Neon database, login, appointment mutations, or AI providers. Lint has no working baseline command. Phase 1 should add focused adapter tests and preserve existing workflows; tooling repairs, if needed, should be scoped and reported separately rather than hidden inside the AI adapter work.
