# Close hand pose crop correction

2026-09-28. Supervisor explicitly authorized fixing the reported excessive crop restriction. LOCAL AND LIVE FIX VERIFIED for the reported input. This changes only local inference input preparation for poses that the previous model path rejected. No training, model, adapter, prompt, inference parameter, remote worker, UI or renderer change.

## Root cause and correction

The exact uploaded Classic Red hand has five valid segmented nails. Original square crop search rejects index, middle and ring because padded neighboring nail support enters every evaluated size. It therefore rejects the whole hand before GPU inference. Thumb and little finger have isolated crops.

`backend/app/nails/localized.py` still runs the entire original isolation search first and returns the same mapping when that search succeeds. If isolation alone fails, it now selects a fully contained target crop within the same evaluated size range with the fewest actual neighboring nail pixels, preferring more context when pixel counts tie. Neighboring pixels are input context. Existing `single_nail_mask`, inverse mapping and both compositing boundaries still prevent pasting onto another nail or outside the final nail mask. No renderer substitution or skipped fingers. Crops missing the target or outside the image still fail with a more accurate framing message.

The reported image now maps all five fingers: thumb 89, index 78, middle 83, ring 76, little 86 normalized pixels per square. Neighbor context on the three newly supported crops is respectively 66, 237 and 10 mask pixels. This is not a claim that generation quality on all close poses is established.

## Local verification

* Exact original upload accepted through crop preparation with the real previously captured detector mask and landmarks.
* Fresh real MediaPipe and isolated YOLO runs on approved source identities 0000000 and 0000088 produce mapping dictionaries and RGB model crops exactly identical to the previous implementation.
* Regression tests exercise both Red and Black on close fingers, including actual neighboring pixels in the crop. A fake model paints the whole crop; only the selected nail can be pasted, and all five nails are edited while surrounding pixels remain unchanged.
* Genuine boundary failures and accepted legacy crops retain their checks. Renderer paths and unified ownership tests retained.
* Full backend: 248 passed, one existing multipart warning. A legacy Makeup configuration test now explicitly clears the unified pair so a developer's active backend `.env` does not invalidate its intended legacy-only case; Makeup code is unchanged.
* No frontend source changed; no repeated frontend build needed.

## Live validation

The first application request used the old already running FastAPI process and reproduced its historical 422 before any GPU call. The identified idle local FastAPI process was refreshed with the correction and its existing bind address. Frontend and Kaggle processes were unchanged. The retried request uses the central `/features/nails/generate` API, the configured shared URL/key, real local hybrid vision/refinement/compositing and the existing unified GPU worker. The protected worker status reports ready, active Nails and foundation load count one. The live request completed HTTP 200 with `inference_path=model`, five edited nails and the approved NAILS-001-LOCAL-v1 adapter hash. End to end wall time was 365.375 seconds (handler 363.297 seconds, GPU HTTP 345.141 seconds, reported model generation 322.810 seconds). Output dimensions are 462 by 663, output PNG SHA-256 `91b86c47c4e7e54c0a80adc4d04cc07d62735a9f0f9e6e4f88a53b21170cd590`. Visual inspection shows red polish on all five nails with recognizable highlights; skin, clothing and background are unchanged. An independent fresh mask reconstruction confirms zero changed pixels outside the final mask, and 7,428 changed pixels inside its 7,428 pixels. Protected unified status after completion verifies five Classic Red crop records on the approved adapter hash, runtime ready, and foundation load count one. The five inference times were 62.686, 62.197, 66.743, 66.791 and 66.839 seconds. This validates the specific correction through the real central API, hybrid path and GPU service. It is not a browser UI test or an all-pose quality claim.

Private input, masks, crop outputs, runtime logs and live response evidence remain under ignored `.tmp/nails-upload-diagnosis/`. No private images, keys or tunnel URL are included in Git. Gate 3 is not passed from this correction alone.
