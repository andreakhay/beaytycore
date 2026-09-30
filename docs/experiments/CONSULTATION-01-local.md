# CONSULTATION-01 local validation

2026-09-30. **LOCAL VERIFIED; NO GPU/LLM TESTED.** The current branch adds only the consultation domain, one router inclusion and the CORS methods needed by its photo and preference endpoints. No image generation was invoked.

| Check | Result |
| --- | --- |
| `cd backend && python -m pytest tests/test_consultation.py tests/test_feature_dispatch.py -q` | 24 passed; one existing `python_multipart` deprecation warning |
| `cd backend && python -m pytest tests -q` | 375 passed; one existing `python_multipart` deprecation warning |
| Default feature catalogs | Mock Hair 6, Makeup 10, Nails 5; consultation tags resolve from active callbacks |
| Expanded Hair registry | The separately configured 13-style file loaded and all 13 style IDs received tags; default three-style registry remained unchanged |
| Photo | Existing validator accepted a 128×96 PNG, stored its exact bytes internally, and returned only a reference and dimensions |
| Provider/validator | All three primary services yielded three distinct deterministic supported styles; invalid IDs, wrong feature/style pairs, disabled styles, duplicates, malformed sets and bad complements failed closed |
| Regression boundary | Test replaced all three generation handlers with exceptions; recommendation completed without invoking any handler |

No Kaggle worker, unified adapter switch, frontend route, booking system or real LLM was used. Service prices and durations are demo estimates only. Expiry and single-process limits are specified in the [architecture record](../specs/0003-consultation-foundation.md).
