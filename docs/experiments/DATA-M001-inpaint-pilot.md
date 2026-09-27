# DATA-M001 source-anchored inpaint pilot

Status: **V1 AND V2 RUN AND REVIEWED; STYLE-CONTROL GATE FAILED** (2026-09-25). This is a replacement candidate for the global Base generation plus V2/V3/V4 preservation route, not an accepted dataset method. Do not generate the remaining 100 targets or train MAKEUP-001 from this pilot.

## Frozen scope and provenance

Eight jobs only: TRAIN identities `003025` and `054109`, each with `natural_makeup`, `soft_glam`, `smoky_glam`, and `classic_red_lip`. Original 512×512 `bare.jpg` portraits are passed as `image`. The exact existing DATA-M001 style instruction plus preservation instruction is passed as `prompt`. No raw FLUX or V4 target image is an input. Parser-derived source semantics and eye/cheek/lip/brow fields from the reviewed V4 pass form the grayscale `mask_image`. Source, parser, and mask hashes are in `plan.json`.

Pinned Base: `black-forest-labs/FLUX.2-klein-base-4B` at `a3b4f4849157f664bdbc776fd7453c2783562f4d`, `diffusers==0.40.0`, `Flux2KleinInpaintPipeline`, FP16, model CPU offload, 512×512, 20 requested steps, guidance 4.0, seed 1977, inpaint strength 0.70. This strength is a single pilot setting, not a tuned optimum. No LoRA is imported or loaded. No TRAIN-001/Hair path is used.

The saved mask is soft and parser-limited to facial skin, source eyelid adjacency, cheeks, lips, and restrained brows. Source eye, nose, inner mouth, hair, and non-face parser labels are black. The pinned Diffusers inpaint class defaults to binarizing its mask. The runner explicitly replaces only `mask_processor` with the same `Flux2ImageProcessor` type configured with `do_binarize=False`, and records this in the load gate. This is required for the soft mask values to reach the pipeline. The inpaint class blends latent samples under the mask, but VAE reconstruction may still change pixels outside zero-mask areas. The runner records that count rather than claiming exact preservation.

The pipeline API and mask behavior were checked against [Diffusers v0.40.0 source](https://github.com/huggingface/diffusers/blob/v0.40.0/src/diffusers/pipelines/flux2/pipeline_flux2_klein_inpaint.py). The pinned model's [model index](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B/blob/a3b4f4849157f664bdbc776fd7453c2783562f4d/model_index.json) lists Base pipeline components. Whether those components load into this inpaint class on the Kaggle T4 is **not yet verified**.

Prepared bundle: `.tmp/data_m001/data_m001_inpaint_pilot_input.zip`, SHA256 `be3c6bfdeba4a54c67733e2b08b4d1f54fc7af4604c8e50c9263cb7247f96059`. It contains `plan.json`, two originals, eight masks, and `data_m001_inpaint_kaggle.py`. ZIP integrity passed. Preparation command:

```powershell
python scripts/data_m001_inpaint_prepare.py --pilot .tmp/data_m001/pilot_results --preserved .tmp/data_m001/preserved_v4b --output .tmp/data_m001/inpaint_pilot_input_v3
```

## Kaggle execution gate

Attach the prepared ZIP to a new Kaggle notebook with a Tesla T4 and Internet enabled. In a first cell, install the proven dependency versions, extract the one attached ZIP to `/kaggle/working/data_m001_inpaint_input`, and confirm `plan.json` is present:

```python
from pathlib import Path
from zipfile import ZipFile
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "diffusers==0.40.0", "transformers==5.0.0", "accelerate>=1.10,<2", "peft>=0.17,<1", "huggingface-hub>=1.23,<2", "safetensors>=0.8,<1", "Pillow>=10.1,<13"], check=True)
matches = list(Path("/kaggle/input").rglob("data_m001_inpaint_pilot_input.zip"))
assert len(matches) == 1, matches
root = Path("/kaggle/working/data_m001_inpaint_input")
root.mkdir(parents=True, exist_ok=True)
with ZipFile(matches[0]) as z:
    assert z.testzip() is None
    z.extractall(root)
print(root, (root / "plan.json").is_file())
```

Run only the load gate first. This imports `Flux2KleinInpaintPipeline`, loads the pinned 4B revision, enables CPU offload, configures a non-binarizing mask processor, and writes `load_gate.json`. It does **not** generate any images. A failed gate records an error and makes a downloadable results ZIP.

```python
subprocess.run([sys.executable, str(root / "data_m001_inpaint_kaggle.py"), "--inputs", str(root), "--output", "/kaggle/working/data_m001_inpaint", "--phase", "verify"], check=True)
```

Only after `load_gate.json` has `success: true`, run the eight-image phase in the same notebook session and output directory:

```python
subprocess.run([sys.executable, str(root / "data_m001_inpaint_kaggle.py"), "--inputs", str(root), "--output", "/kaggle/working/data_m001_inpaint", "--phase", "generate"], check=True)
```

Download `/kaggle/working/data_m001_inpaint_results.zip` before ending the Kaggle session. It includes originals, masks, plan, load gate, per-image PNG and JSON or failure JSON, a summary, and two `Original | Mask | Inpaint` review sheets. Each result stays `PENDING_HUMAN_REVIEW`. Failed images remain recorded. The second phase refuses to run without a successful load gate for the identical plan hash.

## Review gate

Compare each of the eight results against its original and mask at full resolution. Record style presence and separation, identity, eye/nose/lip/jaw geometry, skin texture, eye/lip cosmetic localization, hair, clothing, background, lighting, expression, and visible artifacts. Inspect the `changed_pixels_outside_zero_mask` diagnostic; a nonzero count is not automatically a failure, but broad non-target drift is. Mark each result `ACCEPT`, `RETRY`, or `REJECT` with a concrete note. Only a reviewed result can support replacing global generation plus preservation; pipeline load or generation success alone cannot.

## Current result

The local CPU preparation succeeded for 8/8 masks and records. The input ZIP passed CRC, and focused local tests passed. The Supervisor ran the Kaggle load-only gate and then the eight-image generation phase on 2026-09-25. The gated load completed in 61.76 seconds with `Flux2KleinInpaintPipeline` on a Tesla T4, Diffusers 0.40.0, FP16/CPU offload, `mask_processor_do_binarize=false`, and no LoRA. The downloaded result ZIP at `.tmp/data_m001/data_m001_inpaint_results.zip` has SHA256 `75343ca397fcc0d297e4dce3ed8680a9a44785fd57b60bd28c089d4fa2b36b03`. Its ZIP CRC passed. It contains exactly eight output PNGs, eight generation JSONs, two originals, eight masks, the gate, plan, summary, and two review sheets. All eight records report success, each image hash matches its record, and the gate plan hash matches the saved plan. Total recorded generation duration is approximately 385 seconds (excluding the second model load); every image took approximately 47 to 49 seconds. The generation summary reports 8 attempted, 8 successful, 0 failed, all pending human review.

## Visual review of the eight outputs

The side-by-side sheets are [003025 Original/Mask/Inpaint](../../.tmp/data_m001/inpaint_results_review/review_sheets/003025.jpg) and [054109 Original/Mask/Inpaint](../../.tmp/data_m001/inpaint_results_review/review_sheets/054109.jpg). Full-resolution images and JSON sidecars are under `.tmp/data_m001/inpaint_results_review/targets/`. These are Codex observations, **not official training-pair ACCEPT decisions**.

| Identity | Requested style | Observed result | Review observation |
| --- | --- | --- | --- |
| 003025 | Natural Makeup | Very close to bare; only tiny eye/lip/complexion differences. | `STYLE_WEAK` |
| 003025 | Soft Glam | Near-identical to Natural; blended shadow, cheek sculpting and satin lip do not read clearly. | `STYLE_WEAK` |
| 003025 | Smoky Glam | No recognizable deep smoky shadow; near-identical to Natural and Soft. | `STYLE_WEAK` |
| 003025 | Classic Red Lip | Distinct rich red lip, plausible on the source closed mouth; identity and scene recognizable. | `PARTIAL_SUCCESS`, candidate for project-lead review, not accepted |
| 054109 | Natural Makeup | Bare or almost bare appearance. | `STYLE_WEAK` |
| 054109 | Soft Glam | Very close to Natural; minimal eye/cheek/lip differentiation. | `STYLE_WEAK` |
| 054109 | Smoky Glam | No recognizable smoky eye look; near-identical to Natural and Soft. | `STYLE_WEAK` |
| 054109 | Classic Red Lip | Clearly red, but unusually heavy/dark color around the open-mouth smile and lower lip; teeth remain visible. | `LIP_LOCALIZATION_ARTIFACT` |

Style separation is inadequate: per-identity mean absolute RGB distance between Natural and Soft is only 0.151/0.184, and between Natural and Smoky only 0.118/0.098, on a 0–255 channel scale (003025/054109). These image-level distances are descriptive diagnostics, not style metrics. Red Lip separates visibly from those three.

Both people remain recognizable, with broadly preserved eye, nose, jaw and mouth geometry. Hair, clothing, background, pose and lighting appear mostly stable on side-by-side inspection; neither source gains an obvious new accessory. Some VAE-wide reconstruction remains: sidecars record 130,342–171,320 changed pixels outside the zero-mask regions per output. Mean absolute RGB difference outside zero-mask areas is about 1.3–1.7/255, so many of these are small per-channel changes, but **outside-mask pixels are not exact**. Skin texture is mostly recognizable, with slight tonal/smoothing changes. No visible evidence supports perfect geometry or texture preservation.

The demonstrated blocker is now narrower than the V4 blocker. Source anchoring improves apparent identity/non-target preservation, but the current strength 0.70 plus predominantly low-valued soft masks and preservation-heavy prompts yields almost no Natural, Soft or Smoky control. Strong red pigment can appear, but the smiling lip example shows that the mask/inpaint boundary still needs review. This pilot does **not** justify freezing the method, accepting eight targets, or expanding to 120.

At this V1 review gate, the next action was to keep the remaining dataset and MAKEUP-001 stopped and investigate the effective mask on the same two identities and four styles. The focused CPU finding and proposed V2 correction follow below. Do not change source pool, taxonomy, Hair, or production runtime. Any new run must preserve the original eight outputs as baseline and receive the same full-resolution visual gate.

## Focused V2 mask correction prepared, not generated

The Supervisor authorized fixing the failed four-style pilot. A CPU investigation confirmed a specific attenuation bug in V1 mask preparation: V4's saved `eye_mask.png`, `cheek_mask.png`, `lip_mask.png`, and `brow_mask.png` already contain V4 per-style strengths, and the inpaint packager multiplied them by *another* per-style weight. At 512 pixels, the V1 Natural mask had a maximum of 67/255 and the V1 Soft mask a maximum of 149/255. The Diffusers v0.40.0 inpaint path [bilinearly downsamples masks to packed latent resolution](https://github.com/huggingface/diffusers/blob/v0.40.0/src/diffusers/pipelines/flux2/pipeline_flux2_klein_inpaint.py); at 32×32 the maxima were only 0.263 and 0.584. Neither style had a latent cell at or above 0.7 opacity. The V1 Smoky mask had only 4–10 cells at or above 0.8, consistent with its weak eye change. This is direct input-path evidence, although only a new GPU run can establish its visual effect.

`scripts/data_m001_inpaint_prepare.py --mask-version v2` divides each saved field by its recorded V4 strength before applying the inpaint-specific style weight. It boosts eye and cheek gradients only within the existing source-anatomy mask. For Classic Red Lip it additionally attenuates opacity inward from the source upper/lower lip boundaries, including the mouth opening, to address the heavy smile edge. **Model revision, prompts, seed, 512 pixels, 20 steps, guidance 4.0, inpaint strength 0.70, and no-LoRA condition stay fixed.** Thus the next eight-image run isolates the mask correction. The original V1 input/results remain preserved.

CPU results for the final V2 bundle:

| Style | Identity 003025 latent maximum, V1 → V2 | Identity 054109 latent maximum, V1 → V2 |
| --- | ---: | ---: |
| Natural | 0.263 → 0.698 | 0.263 → 0.698 |
| Soft Glam | 0.584 → 0.898 | 0.584 → 0.898 |
| Smoky Glam | 0.910 → 1.000 | 0.910 → 1.000 |
| Classic Red Lip | 0.918 → 0.776 | 0.918 → 0.776 |

The same eight source/style cells are packaged at [V2 input ZIP](../../.tmp/data_m001/inpaint_v2_release/data_m001_inpaint_pilot_v2_input.zip), SHA256 `98f6524d5b4184a477322c01ffd6e3ad97c4614f85c3d7b6d573db093bdcee8c`. ZIP CRC passed, eight source/mask plan records validate, parser-protected source labels remain zero in all masks, and 35 focused CPU tests passed. The packaged runner writes `progress.json` and flushed stage/job messages so Kaggle model loading and generation can be distinguished. It names its results ZIP from the output directory, preventing a V2 run from replacing the previous Kaggle ZIP. The V2 run and review follow; no DATA-M001 target is accepted.

## V2 Kaggle run and visual gate

The Supervisor ran the V2 load gate and eight-image generation on a Kaggle Tesla T4 and downloaded the result ZIP. The first load attempt did not produce a gate; a required `text_encoder/generation_config.json` was found missing from the local Hugging Face snapshot, fetched, and the offline monitored retry loaded successfully in 55.83 seconds. This establishes the successful retry, not a definitive cause for the earlier delay. The gate records Diffusers 0.40.0, pinned Base revision, `Flux2KleinInpaintPipeline`, FP16/CPU offload, non-binarizing mask processor, no adapter and no LoRA.

The downloaded [V2 result ZIP](../../.tmp/data_m001/data_m001_inpaint_v2_results.zip) is 4,117,383 bytes, SHA256 `cbf7484859a5f24dbb6a1d724f78f9d1ca894b8c3de1c8acc411ff4579b96622` and passed ZIP CRC. It contains the two originals, eight masks, plan, load gate, progress, eight full-resolution outputs and JSON sidecars, summary, and two review sheets. The gate matches the saved plan hash; all eight source, mask and output hashes match the plan/records. The summary reports 8 attempted, 8 successful, 0 failed, `PENDING_HUMAN_REVIEW` and no LoRA. Recorded image generation durations total 389.21 seconds (46.52–49.90 seconds each), excluding model load. No larger run was performed.

The visual sheets are [003025 Original/Mask/Inpaint](../../.tmp/data_m001/inpaint_v2_results_review/review_sheets/003025.jpg) and [054109 Original/Mask/Inpaint](../../.tmp/data_m001/inpaint_v2_results_review/review_sheets/054109.jpg). Full-resolution PNGs are under `.tmp/data_m001/inpaint_v2_results_review/targets/`. These are Codex review observations, **not official training-pair ACCEPT decisions**.

| Identity | Style | V2 visual observation |
| --- | --- | --- |
| 003025 | Natural Makeup | Still close to bare; makeup signal too weak to label confidently. |
| 003025 | Soft Glam | Visible pale/silver eye pigment and light lip, but the eye look is unnatural for the requested soft glam and cheek sculpting is weak. |
| 003025 | Smoky Glam | Slight darkening near eyes, but no clearly deep, blended smoky style; close to Natural. |
| 003025 | Classic Red Lip | Red lip is recognizable with a softer boundary than V1, but the color is muted; candidate for human review only. |
| 054109 | Natural Makeup | Almost bare; no reliable natural-makeup condition. |
| 054109 | Soft Glam | Very close to Natural; style remains weak. |
| 054109 | Smoky Glam | Mild eye darkening, not a distinct smoky-glam appearance. |
| 054109 | Classic Red Lip | Smile lip boundary is less heavy/dark than V1 and teeth remain visible; plausible but less saturated, pending human review. |

Both identities, overall face shape, expression, hair, clothing and background remain apparently stable in the comparison sheets. This is not exact pixel preservation: the sidecars report 130,195–171,313 changed pixels outside the zero-mask region after VAE decoding. An image-level diagnostic (mean absolute RGB difference from Natural, 0–255 scale) shows Soft/Smoky separation of 2.042/0.300 for 003025 and 0.212/0.216 for 054109, respectively. The 003025 Soft difference is driven substantially by pale eye pigment, not successful class fidelity; these distances are **not** a makeup-quality metric.

V2 corrected an actual input attenuation error and improved some visible changes, especially the smiling Red Lip boundary, but it did **not** pass the four-style dataset gate. Natural, Soft and Smoky remain insufficiently distinct across the two identities, and 003025 Soft has an eye-color artifact. The source-anchored method remains experimental; no output is accepted for DATA-M001 training. Keep the remaining 100 targets and MAKEUP-001 training stopped. The next decision should address this concrete style-control failure before another GPU run, rather than infer success from 8/8 generation or increase mask opacity blindly.
