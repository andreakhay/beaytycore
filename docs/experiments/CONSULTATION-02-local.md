# CONSULTATION-02 local integration evidence

2026-09-30. **LOCAL/MOCKED VERIFIED; LIVE KAGGLE NOT TESTED.** CONSULTATION-01 checkpoint `52902cf` is preserved on the parent branch. CONSULTATION-02 implementation commit: `7ecae09`. This branch adds consultation generation and UI only; no remote worker, adapter, prompt or model file was changed.

| Check | Result |
| --- | --- |
| Focused backend consultation tests | `cd backend && python -m pytest tests/test_consultation_generation.py -q`: 10 passed. Includes canceled caller keeping the generation slot until the handler finishes. Existing CONSULTATION-01 cases also passed during the full suite. |
| Real handler boundary with synthetic remote | `test_consultation_uses_real_handlers_and_hybrid_nails_with_synthetic_remote`: Hair, Makeup and Nails each traverse consultation → central dispatcher → original handler; Nails model style makes five synthetic crop calls and renderer style makes zero added remote calls. No GPU. |
| Local mock browser integration | `cd frontend && $env:CONSULTATION_LOCAL_MOCK='1'; npm run test:e2e -- consultation-local.spec.ts`: 3 passed with all three backend engines explicitly checked as mock before generation. Browser → consultation API → original feature handlers → mock result → three cards → Select. |
| Mocked browser behavior | `frontend/e2e/consultation.spec.ts` covers exactly three progressive cards for all features, failed second look with manual retry only, three Custom photo transfers, malformed two-item response rejection, and narrow screen fit. |
| Backend full regression | `cd backend && python -m pytest tests -q`: 385 passed; one existing `python_multipart` deprecation warning. |
| Frontend browser regression | `cd frontend && npm run test:e2e`: 42 passed, 11 skipped (the prior synthetic remote suite and the new explicit local-mock suite require opt-in). |
| Frontend lint/build | `cd frontend && npm run lint`: passed. `cd frontend && npm run build`: passed, including `/consultation` prerender and TypeScript. |

No actual Kaggle session or private user photo was used. Existing fixture portrait and synthetic Nails geometry/remote responses were used. The backend store retains image payloads only within its existing one-hour/process-local lifetime. The next validation gap is representative live consultation generation through the current unified worker, then CONSULTATION-03 conversational provider work as a separate phase.
