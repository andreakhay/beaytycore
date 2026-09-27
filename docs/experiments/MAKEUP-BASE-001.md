# MAKEUP-BASE-001: three style FLUX Base pilot

Status: **PREPARED, NOT RUN ON GPU, NOT REVIEWED**. Evidence status: **NEEDS VERIFICATION** for all visual questions.

## Research gate

Use three consented, mostly frontal portraits with visible faces and varied facial features or skin tones. Use the same portraits for Natural Makeup, Soft Glam, and Smoky Glam, for exactly nine attempted edits. Do not expand to the other seven styles until these nine are technically successful and manually reviewed. The application Makeup shell and all Hairstyle training, data, adapters, registry, inference, and expansion remain outside this experiment.

The standalone runner is [`notebooks/makeup_base_001_kaggle.py`](../../notebooks/makeup_base_001_kaggle.py). It imports only the Makeup candidate catalog and prompt text. It loads `black-forest-labs/FLUX.2-klein-base-4B` at revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, FP16, CPU offload to CUDA device 0, 512 by 512, 20 steps, guidance 4.0, seed 1977 for each edit. It creates a fresh Base pipeline and does not load a LoRA. The run plan, runtime record, and each generation record say `adapter_id: null` and `lora_active: false`. The source code is the stronger evidence that no adapter load occurs. A real Kaggle run is still required to verify the operating environment.

Portrait preparation applies EXIF transpose, RGB conversion, and aspect preserving padding to 512 by 512 using RGB (245, 245, 245). Save the original alongside that normalized input. This preprocessing may visibly alter a transparent or oddly framed input, so review both versions. Portraits must have distinct safe filename stems. Keep personal portrait files out of Git.

## Execution and evidence

From the repository root in a Kaggle GPU session, with exactly three consented JPG or PNG portraits in the input directory, run:

```text
python notebooks/makeup_base_001_kaggle.py --phase plan --inputs /kaggle/input/makeup-portraits
python notebooks/makeup_base_001_kaggle.py --phase pilot --inputs /kaggle/input/makeup-portraits --output /kaggle/working/makeup_base_001 > /kaggle/working/makeup_base_001_pilot.log 2>&1
```

The plan should show `portrait_count: 3`, `job_count: 9`, and only `natural_makeup`, `soft_glam`, and `smoky_glam`. Do not invoke an all style phase. Preserve the output directory and the stdout/stderr log before the Kaggle session expires. A stalled or failed Base load writes `base_load_trace.log` or `base_load_failure.json`. Each successful edit writes the full resolution PNG and `generation.json`; a generation exception writes `failure.json` and stops so no failure is silently lost. Existing successful outputs are reused only after their metadata and output hash match.

Per output metadata includes source identity, source file SHA 256, style ID and name, exact prompt, seed, model ID and revision, preprocessing, dimensions, steps, guidance, dtype, CPU offload, start and finish time, duration, output path and hash, review status, and no LoRA status. Originals and normalized inputs are retained separately. `runtime.json` records library versions, GPU, and Base load duration. `review_sheets/pilot_contact_sheet.jpg` puts each identity on one row with Original, Natural Makeup, Soft Glam, and Smoky Glam columns. The contact sheet is a review aid, not a substitute for the full resolution outputs.

## Manual review record

Inspect each generated PNG beside its raw original and normalized input. For each of the nine outputs, record one primary state from `ACCEPTABLE_BASELINE`, `PARTIAL_SUCCESS`, `STYLE_WEAK`, `IDENTITY_DRIFT`, `NON_TARGET_DRIFT`, `GEOMETRY_DRIFT`, or `GENERATION_FAILURE`, plus any additional applicable failure notes. These are structured observations, not quantitative metrics. Record concise evidence for:

1. Whether the requested makeup is visible and whether the three looks are meaningfully separated for the same identity.
2. Whether the person is clearly the same, with eye shape, nose structure, jaw and face shape, and mouth and lip geometry preserved.
3. Whether cosmetic changes stay on appropriate eyes, brows, cheeks, lips, and complexion regions.
4. Any unwanted hair, hair color, clothing, background, pose, lighting, or expression changes.
5. Unrealistic skin, strange eyes, malformed lips, asymmetry, over smoothing, duplicated features, accessories, or other artifacts.

Do not classify generation alone as successful makeup. Preserve a per image review record with the output archive and summarize contradictions as well as positive results.

## Evidence available on 2026-09-24

The local CPU tests show the plan selects exactly nine jobs for three supplied test images, with no LoRA in the plan, and the contact sheet layout is 3 by 4. These test images are synthetic and are not pilot portraits. There are no three suitable consented pilot portraits in the workspace, no accessible Kaggle session in the desktop browser, and no local CUDA run. **Base loading, generation, style fidelity, style separation, identity, facial geometry, localization, and non target preservation remain unobserved.** A separate DATA-002 runtime result cannot serve as MAKEUP-BASE-001 evidence.

### Portrait selection audit, 2026-09-24

The workspace search found no three eligible Makeup pilot portraits. `data/source/FaceSketches-HairStyle40.zip` and `data/dataset_v1/` contain Hair dataset photographs. The dataset card declares Apache-2.0, but the project record explicitly says individual upstream photograph rights were not independently established. DATA-001 and DATA-002 assets are also outside this pilot's protection boundary, so none was selected or copied. The `frontend/e2e/fixtures/portrait.png` image is a 2,869-byte synthetic test fixture, not one of three real identities. Audit and selection sheets under `docs/data/` are Hair evidence, not independent Makeup source portraits. No staged Makeup portraits exist. Per the Supervisor's stop condition, Kaggle access, CUDA, Base loading, and generation were not attempted in this task. Attempted/successful/failed generations remain 0/0/0; no contact sheet or output archive exists.

### Downloaded candidate check, 2026-09-24

Three distinct, visually usable frontal portraits are now present as `D:/Downloads/nomakeup1.jpg`, `nomakeup2.jpg`, and `nomakeup3.jpg`. Their SHA-256 hashes are `dafa7701e0d585cdbae441fefb39260243602c22ecd7cf871ad0c50f69bddf5f`, `7450d2743d91c350531cfcdbef851e757b3ab83a362806b6b86508edd6c97031`, and `96c6b67fc6d0caa4abc5e7722301c8f0ebb113fd08b1a06270ab0e387aa3ac44`, respectively. The Supervisor says they were downloaded from Pinterest, but has not supplied original source URLs, photographer/rights holder, license, or permission. Pinterest's own copyright guidance says permission to use images found there should, where necessary, be sought from the copyright holder. A Pinterest download alone does not satisfy this experiment's provenance and rights gate. Therefore none was staged, no Kaggle run was attempted, and generation counts remain 0/0/0.

### Limited pilot handoff, 2026-09-24

The Supervisor subsequently directed use of these three downloaded files for this private experiment despite the unresolved provenance. They were copied, without altering the originals, to ignored local paths `.tmp/makeup_base_001/inputs/portrait_01.jpg` through `portrait_03.jpg`. Copy hashes match the three hashes above. These images must not be treated as licensed or consented Makeup dataset sources and must not be published from this work. A Kaggle upload bundle is at `.tmp/makeup_base_001/makeup_base_001_kaggle_bundle_v2.zip`; it contains only the three portraits, the isolated runner, and the Makeup catalog. The extracted bundle passed a local plan check: three portraits, nine jobs, the three requested styles, and `lora_active: false` in the plan. The Codex browser could reach Kaggle but was signed out, with no access to the user's new notebook. The Supervisor chose to run the Kaggle notebook directly. No Kaggle GPU, CUDA, Base load, generation, or image review result has been received yet; attempted/successful/failed counts remain 0/0/0 from Codex-observed evidence.

### First Kaggle handoff correction, 2026-09-24

The Supervisor reported `GPU: Tesla T4` after a successful `torch.cuda.is_available()` assertion and successful `Flux2KleinPipeline` import. The first notebook cell then failed before model loading at its ZIP discovery assertion, `Expected one uploaded bundle, found: []`. The uploaded input was mounted at `/kaggle/input/datasets/cosme001/makeup-base-001-kaggle-bundle-v2`, apparently as an extracted dataset directory. The original handoff incorrectly required the ZIP filename to remain visible. A local reproduction against the extracted bundle had zero ZIP matches but one `notebooks/makeup_base_001_kaggle.py` match and three portrait files. The corrected handoff locates the runner in the mounted directory and uses its parent as the bundle root, falling back to ZIP extraction only if a ZIP is actually present. The Flax deprecation message was a warning, not the failure. Base load and generation have still not been attempted or verified; counts remain 0/0/0.

### Kaggle execution reported, artifact review pending, 2026-09-24

The Supervisor reran the corrected cell. Its plan assertion passed for three portraits, nine jobs, the requested three styles, and `lora_active: false`. The pilot subprocess returned exit code 0 on a reported Tesla T4. The supplied tail of `pilot_console.log` shows `portrait_03 soft_glam: 72.9s`, `portrait_03 smoky_glam: 73.3s`, and a review sheet path `/kaggle/working/makeup_base_001/review_sheets/pilot_contact_sheet.jpg`. Kaggle created `/kaggle/working/makeup_base_001_results.zip`. This supports a reported completed runner execution and implies Base loaded, but the archive, runtime record, nine generation sidecars, image hashes, and images have **not** been independently inspected by Codex. Therefore attempted/successful/failed counts are not yet artifact verified, and all visual questions remain NEEDS VERIFICATION. The Supervisor has been asked to download the ZIP before the session ends and provide it for integrity and manual image review.

### Downloaded artifact verified and reviewed, 2026-09-24

The ZIP was downloaded to `D:/Downloads/makeup_base_001_results.zip`, and its archive integrity, nine sidecars, nine generated images, zero failure records, source and output hashes, exact configuration, and contact sheet were checked locally. All nine full resolution outputs were reviewed against the originals. The detailed per-image findings and decision are in [MAKEUP-BASE-001 pilot review](MAKEUP-BASE-001-review.md). The ZIP is sufficient for local review, so the Kaggle GPU session may end. Technical completion is verified, but quality is mixed: Base can produce distinguishable makeup-like changes for some identities while often reconstructing facial geometry and skin; one Smoky result has implausible eye localization. The three-style gate does not clear expansion to ten styles or dataset work.

## Decision

The reviewed pilot supports a separate identity and facial-geometry preservation investigation before taxonomy expansion or DATA-M001. Do not run all ten styles, add face parsing, train MAKEUP-001, or integrate live Makeup inference from this evidence. The three Pinterest sourced portraits remain an experimental exception with unresolved rights, not approved future dataset material.
