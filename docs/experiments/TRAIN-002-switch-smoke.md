# TRAIN-002 T4 adapter-switch smoke

Status: **VERIFIED routing and restoration, including downloaded artifact inspection**. On 2026-09-25, the Supervisor ran the isolated localhost smoke with one Kaggle T4 and the combined handoff containing frozen TRAIN-001 and derived TRAIN-002 adapters. The code exited 0 and printed `TRAIN-002 SWITCH SMOKE PASS`. No public tunnel or local web-app request was part of this smoke.

## Reported checks

- Runtime: Python 3.12.13, PyTorch 2.10.0+cu128, CUDA 12.8, Tesla T4 with 14.56 GiB reported VRAM.
- Base: `black-forest-labs/FLUX.2-klein-base-4B@a3b4f4849157f664bdbc776fd7453c2783562f4d` loaded once.
- Verified adapter hashes: TRAIN-001 `7e3991f8a4e502573d3e82e9ac34c89fdf3f0b66fb337abb026a5b4c9ad080ff`; TRAIN-002 `59d527217a68139bc2aaa4eedbfcd2d5789ef115f8ecb924410eea24a952939b`.
- Local server reported READY with both adapters and thirteen smoke-registry styles. The live application registry remains unchanged with only the three TRAIN-001 styles.

| Request | Style | Adapter | Seconds | Peak GPU MiB | Output SHA-256 |
| --- | --- | --- | ---: | ---: | --- |
| 1 | `crew_cut` | TRAIN-001 | 64.93 | 8302.2 | `ac09c8744e5fa693190a69f2595375bd5edf1bda3c2a49b6f7e32deb2e0e9aa3` |
| 2 | `pixie_cut` | TRAIN-002 | 62.68 | 8304.3 | `14b6c33b0b3680079248f9312b359ab9d03aa2d9eb22766de9c1bca3d4ff5786` |
| 3 | `crew_cut` | TRAIN-001 | 63.35 | 8304.3 | `ac09c8744e5fa693190a69f2595375bd5edf1bda3c2a49b6f7e32deb2e0e9aa3` |

The Supervisor downloaded `D:/Downloads/train002_switch_smoke.zip` (175,899 bytes; SHA-256 `ae6defe53bb361f297f8ab9a4e347a93323f6e596ea4fb0b09ed336b69fcc94b`). Local inspection found four members, no ZIP CRC error, a `PASS` report, and three decodable 512×512 RGB PNGs whose hashes match the report. The two TRAIN-001 responses are byte-identical under the same input, prompt, seed, and generation settings. The smoke code also checked each response's adapter ID/hash and `/health` active adapter after each request. The final health check reported TRAIN-001 active. This verifies routing and restoration on the T4.

## Limits and next gate

The input fixture is a simple illustration rather than a real portrait. Its generated faces are not evidence of realistic portrait quality or identity preservation. This is a routing test, not a ten-style quality verdict or public app integration. The held-out TRAIN-002 sheet remains preliminary, including concerns for `curtain_hair`, `pompadour_undercut`, and `side_part_undercut`. A separate live registry/inference handoff is required before the local app can expose any TRAIN-002 style. Preserve TRAIN-001 as the fallback.
