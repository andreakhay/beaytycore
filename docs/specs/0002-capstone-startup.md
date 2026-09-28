# 0002. Capstone startup automation

2026-09-28. **CONFIRMED scope; IN PROGRESS implementation; fresh session NEEDS VERIFICATION.** Authority: Supervisor delegates selection of a small discovery mechanism and authorizes additive startup automation. AI architecture, settings and GPU ownership remain unchanged.

## Decision before implementation

No endpoint registry is evidenced in the project. Use ntfy.sh as a temporary HTTP mailbox, not an inference service. Kaggle explicitly publishes a small signed endpoint record; the laptop reads only its latest cached message. No account, extra publisher token, database or hosted application is required. GitHub Gists are the runner up but add write-token setup and durable URL history. Existing GitHub CLI authentication is unavailable; no repository configuration is changed.

The mailbox topic and HMAC signing key are derived separately from the existing random unified API key. The record contains no API key or images. Verify signature, exact schema, publication UUID, four-hour expiry, approved bundle/version and HTTPS Quick Tunnel root before any worker request. Then check public health and authenticated status for ready/idle, pinned Base, load count one and all features. Only the newest record is considered, never an older fallback. Publish signed starting/failed records without endpoints to invalidate previous publications. No inference retries are introduced.

Failure: the external mailbox can be unavailable, evict cached messages, rate limit or receive an invalid newer message. Startup fails with its stage and an explicit manual URL override. Four-hour expiry bounds replay; re-running START CAPSTONE on the same healthy session republishes without another Base load. This is a temporary demo dependency, not an uptime guarantee. [ntfy publishing/cache](https://docs.ntfy.sh/publish/), [latest cached message API](https://docs.ntfy.sh/subscribe/api/), [anonymous use/privacy](https://docs.ntfy.sh/privacy/).

## Implementation boundary

2026-09-28 approved extension: the Supervisor requested TRAIN-002 support after a catalog mismatch. Prepare one separate private candidate with unchanged existing adapter bytes and optional registry. Preserve the original package/notebook as fallback. A wrapper supplies expanded Hair configuration only at the existing worker subprocess boundary, preserving historical Gate checks, one foundation and ownership. The signed exact bundle identity selects the matching local registry without `.env` edits. Expanded unified GPU inference requires a live check before acceptance.

2026-09-28 correction: publication acknowledgement is not a guarantee of immediate cache visibility. Confirm the exact signed ready publication with bounded startup metadata polling and fresh HTTP reads before declaring ready. The laptop still rejects nonready, invalid and stale records immediately. No generation retries or older endpoint fallback are added. Reload only downloaded startup support modules when rerunning the entry cell in the same notebook kernel, so a running worker can be safely reused after a support fix.

Keep `deployment01_20260928_v2.bin` byte-identical. Download only two public support scripts from a pinned Git commit with pinned source hashes in a thin new notebook entry cell. Verify/extract the original package, then run its unchanged exact-environment bootstrap in a subprocess. Worker, models, adapters and Gate 2 owner are untouched. The orchestrator stages setup/publication and supports safe re-entry for its own verified healthy runtime. Notebook settings/dataset/Secrets remain one-time manual platform setup.

Windows START/STOP batch files call a Python launcher. Read the existing ignored backend `.env` without writing it; process environment overrides its defaults. Discover/verify then start a hidden supervisor, backend and Next dev process with logs under ignored `.tmp/capstone/`. A Windows Job Object contains only launcher-owned children and closes them on shutdown/supervisor death. An authenticated loopback control server records launcher ownership. Never kill processes merely by port/name. Occupied unmanaged ports fail clearly. Repeated launch reuses the same verified managed session or stops its owned older processes before replacement. A short atomic launch lock prevents competing launches.

## Acceptance and limits

Local tests cover signed publication/discovery, expiry/identity, secret exclusion, process env/no file mutation, startup failure/re-entry/shutdown and existing diagnostic/rollback regressions. No GPU inference during preparation. The fresh rehearsal uses START CAPSTONE, START_CAPSTONE.bat, then the existing four-request application smoke and evidence collection. CAPSTONE READY means startup checks passed, not CAPSTONE_DEPLOYMENT_READY. The latter still requires returned fresh-session review.
