# MAKEUP-BASE-001 pilot review

Date: 2026-09-24. Evidence status: **VERIFIED local artifact integrity; EXPERIMENTAL visual observations**. This is a nine-image qualitative pilot, not a benchmark or a claim of trained Makeup support.

## Artifact integrity and configuration

The downloaded archive is `D:/Downloads/makeup_base_001_results.zip`, 2,047,044 bytes, SHA-256 `2a4fb7c21c9fada16489c9654277a84ce303846fcbba4a5da7867507450fb2f7`. It passed a ZIP CRC check, contained no unsafe archive paths, and was extracted for review under ignored `.tmp/makeup_base_001/results/makeup_base_001/`. It contains nine `generation.json` records, nine `generated.png` images, zero `failure.json` records, all three raw originals and normalized sources, `runtime.json`, `pilot_console.log`, the plan files, and `review_sheets/pilot_contact_sheet.jpg`. All nine output hashes, original source hashes, and normalized source hashes match their sidecars. All nine image sidecars report success, a positive duration, exact prompts and timestamps, model revision, and the expected 512 by 512, 20 step, guidance 4.0, seed 1977 configuration.

The runtime record reports Python 3.12.13, PyTorch 2.10.0+cu128, Diffusers 0.37.1, CUDA 12.8, Tesla T4, and Base load time 114.57 seconds. It names `black-forest-labs/FLUX.2-klein-base-4B` at revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`. The isolated runner source contains no adapter load call; the runtime and all nine sidecars record `adapter_id: null` and `lora_active: false`. This is configuration and code path evidence, not independent introspection of every module in the live pipeline.

Verified counts: **9 attempted, 9 successful files, 0 recorded generation failures**. Durations range from 63.13 to 73.68 seconds per output. The successful file and hash checks establish execution, not cosmetic quality.

The three input files were user-selected Pinterest or stock-like downloads. Exact original URLs, rights holders, licenses, and subject permission remain unverified. They were used only for this private pilot at the Supervisor's direction. Do not publish the portraits or generated derivatives or reuse them as DATA-M001 sources without separate rights review.

## Manual image review

Each generated PNG was inspected at full 512 by 512 resolution against its normalized source, alongside the 3 by 4 contact sheet. Labels below are structured qualitative observations and are not quantitative metrics. Additional notes may apply to the same output.

| Identity | Style | Primary state | Observations |
| --- | --- | --- | --- |
| `portrait_01` | Natural Makeup | `IDENTITY_DRIFT` | Visible makeup, but far heavier than natural. Eyebrows become thick and sculpted; eyes look larger; nose and lips appear reshaped; face and skin become airbrushed. Hair silhouette and white background largely stay put. Also `GEOMETRY_DRIFT`, excessive smoothing. |
| `portrait_01` | Soft Glam | `IDENTITY_DRIFT` | Polished eyes and lips are recognizable as glam, but the result resembles a different, highly retouched person. Eye, brow, nose, lip, and face proportions drift. Hair and background remain largely stable. Also `GEOMETRY_DRIFT`, excessive smoothing. |
| `portrait_01` | Smoky Glam | `IDENTITY_DRIFT` | Strong dark eye makeup differs from the softer looks, but heavy brows and reconstructed facial features persist. Hair and background remain largely stable. Also `GEOMETRY_DRIFT`, overdone eye makeup and smoothing. |
| `portrait_02` | Natural Makeup | `ACCEPTABLE_BASELINE` | Subtle complexion and eye/lip polish with the clearest identity preservation in this pilot. Slight smoothing and facial highlight change. Hair, background, pose, and shoulders appear stable. |
| `portrait_02` | Soft Glam | `STYLE_WEAK` | Makeup is barely stronger than Natural and appears somewhat uneven around the eyes; the two styles are not well separated for this identity. Overall face and non-target scene remain fairly stable. Also eye asymmetry note. |
| `portrait_02` | Smoky Glam | `PARTIAL_SUCCESS` | Clearly distinct smoky intent, but eye color becomes a blocky black mask that extends too broadly toward the brows and sides. This is an implausible localization/artifact failure; eye appearance changes substantially. Hair, background, pose, and shoulders remain stable. |
| `portrait_03` | Natural Makeup | `IDENTITY_DRIFT` | Cosmetic color is visible, but skin texture is erased and eyes, nose, lips, and face contour look reconstructed. The person is less recognizably the same. Hair, background, pose, and shoulders remain largely stable. Also `GEOMETRY_DRIFT`, excessive smoothing. |
| `portrait_03` | Soft Glam | `IDENTITY_DRIFT` | Stronger eye and cheek styling separates from Natural, but the face remains doll-like and structurally altered. Hair/background remain stable. Also `GEOMETRY_DRIFT`, excessive smoothing. |
| `portrait_03` | Smoky Glam | `IDENTITY_DRIFT` | Dark eye makeup is distinct, but facial reconstruction and very smooth skin persist; eye shape and lip/face proportions differ from source. Hair/background remain stable. Also `GEOMETRY_DRIFT`, overdone styling. |

No clothing preservation claim is possible from these portraits: all three frame bare shoulders and show no discernible clothing. Hair color and hairstyle are mostly stable in this set, with possible small tonal changes from retouching rather than a clear hair edit. The simple studio backgrounds and fixed poses are mostly preserved. Lighting on the face changes through synthetic makeup and smoothing; the background lighting is comparatively stable. Expression is broadly preserved, though changed facial geometry can alter perceived expression. Visible color generally lands on face regions, but `portrait_02` Smoky Glam is not plausibly confined to ordinary eye makeup.

## Style separation and decision

The three requested looks are not consistently controlled. `portrait_01` and `portrait_03` show a visible progression from lighter to darker eye makeup, but even Natural is too glamorous and the face is substantially reconstructed. `portrait_02` preserves identity better for Natural and Soft, yet those two looks are weakly separated; Smoky is clearly different but implausibly mask-like. This contradicts the hoped-for combination of distinct styles **and** stable identity from prompt-only Base editing.

The evidence supports that pinned Base can respond to text instructions and produce visible makeup-like changes while often preserving gross hair and background composition. It does **not** support acceptable identity, facial geometry, skin realism, or reliable style separation across identities. Nine outputs on three low-resolution studio portraits do not establish behavior on varied backgrounds, clothing, poses, skin tones, or higher-resolution inputs. No conclusion about MAKEUP-001 training, face parsing, or masking follows directly from this pilot.

**Recommendation:** stop at the three-style gate. Do not expand to all ten or begin DATA-M001. First design a separate, tightly scoped identity and facial-geometry preservation experiment using permitted portraits, with Natural and Soft prompts adjusted only after the preservation failure is understood. Treat Smoky localization as an additional prompt/control problem, not proof that simple face compositing will solve geometry drift.
