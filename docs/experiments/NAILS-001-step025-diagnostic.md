# NAILS-001 step-25 failure diagnostic — 2026-09-26

**Status: DONE AS DIAGNOSTIC; ROOT CAUSE NOT ISOLATED.** The training path, edit signal, inference-only train-split probe, and visual review are recorded here and in the [train-split review](NAILS-001-step025-trainset-review.md). No training was resumed, and NAILS-001 remains disconnected from the app.

## Inputs and integrity

- The byte-identical approved `DATA-N001-final.zip` was rehashed at SHA-256 `d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb`. Its prior Kaggle preflight logged 100 accepted pairs, 80 train/20 validation, a fixed disjoint 16/4 identity split, verified per-member reference/target/mask hashes, captions, and training-config SHA-256 `d5232482c4389170ea69edb3664796762b3a44c00a7e7801f2d093309afeab31`. The experiment bundle's downloaded config matches [the retained config](NAILS-001-step025-logs/train_config.yaml).
- The step-25 adapter SHA-256 is `34bf82238dfcc8e6365cd9fa6b63d36700312780f2e396dc6d91f7cc3f829c91`. The optimizer was safely loaded with `torch.load(..., weights_only=True)` solely to inspect top-level keys: `state` and `param_groups`; no sampler or RNG state was present.
- The run used AI Toolkit commit `a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7`, fetched unchanged into ignored `data/nails/work/ai-toolkit-a8df/` for this code audit. [Pinned upstream source](https://github.com/ostris/ai-toolkit/tree/a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7).

## Actual paired-edit path

| Stage | Inspected behavior | Evidence |
| --- | --- | --- |
| DATA-N001 | `train/target/{pair_id}.png`, `train/reference/{pair_id}.png`, `train/target/{pair_id}.txt`, and `train/masks/{pair_id}.png` exist under matching names. All five style captions describe edits and equal their manifest records. | Approved archive, `scripts/nails001_kaggle_pilot.py:49-101`, [Kaggle preflight](NAILS-001-step025-logs/preflight_data.json) |
| Training config | `folder_path` points to train targets; `control_path` points to train references; `caption_ext: txt`; resolution 512; batch size and accumulation one; 25 steps; `flux2_klein_4b`. There is no validation folder or mask path in the training dataset config. | [Config](NAILS-001-step025-logs/train_config.yaml) |
| Dataset loader | The target folder's PNGs become file items. Captions load from same-stem `.txt`. References are found by same stem in `control_path`; target and reference are separately opened and transformed. The run log reports 80 files in a single 512×512 bucket. | Pinned `toolkit/data_loader.py:442-538, 592-661`; `toolkit/dataloader_mixins.py:336-373, 958-1018, 1118-1153, 1177-1248`; [log](NAILS-001-step025-logs/train.log) |
| Preprocessing | Both files are already 512×512 RGB. Defaults are `random_crop=False`, `random_scale=False`, `buckets=True`, `standardize_images=False`, `num_repeats=1`, `num_workers=2`. The bucket resize/center crop is therefore an identity size/crop for these square images. The target is converted to a tensor in `[-1,1]`; the reference is loaded in `[0,1]` and mapped to `[-1,1]` in the FLUX model. No random flip/augmentation is configured. | Pinned `toolkit/config_modules.py:947-1051`, `toolkit/data_loader.py:460-475`, `toolkit/dataloader_mixins.py:958-1009, 1209-1248`, `extensions_built_in/flex2/flex2.py:504-521` |
| Toolkit batch and model | The target tensor is VAE encoded as `batch.latents`. The reference is `batch.control_tensor`; FLUX's edit path VAE encodes it and concatenates its latent with the noisy target latent before transformer prediction. Text embeddings come from the target's edit caption. The flow-matching loss target is `noise - batch.latents`. Default `control_dropout` is zero. | Pinned `jobs/process/BaseSDTrainProcess.py:1097-1138`; `extensions_built_in/sd_trainer/SDTrainer.py:1737-1751, 2159-2162, 2233-2262`; `extensions_built_in/flex2/flex2.py:77, 305-317, 338-350, 373-376, 469-527` |
| Nail masks | The training config has no `mask_path`; therefore `batch.mask_tensor` is absent and the mask-weighted loss branch is not entered. Masks were used for deterministic target construction and evaluation compositing, not direct training supervision. | Pinned `extensions_built_in/sd_trainer/SDTrainer.py:1555-1575`; config above |

**Conclusion:** Static config, approved files, pinned loader/model code, and the 80-file runtime log support a correctly paired **image-edit** training path. They do not include a per-batch tensor dump, so actual runtime reference pixels at each step are not independently proven. No reference/target swap, caption mismatch, validation leakage, or text-to-image-only config was found. No PATH D configuration error is established.

## Which pairs did steps 1–25 see?

**Exact IDs are not recoverable from retained evidence.** The pinned loader calls Python `random.shuffle` on the 80-file bucket, then builds a PyTorch `DataLoader(shuffle=True)` with two workers. The trainer creates an iterator and takes one batch per step (`jobs/process/BaseSDTrainProcess.py:2490-2493, 2528-2595`). The initial seed launcher set Python/NumPy/Torch to 1977, but the run did not log the directory enumeration, sampler order, per-step filenames, or RNG/sampler state. Model setup consumed RNG before the loader iterator; replaying a simple seed permutation would invent an exact order. The log shows no image-load replacement error and the loader samples without replacement in this first epoch, so **25 distinct of 80** is the strongest code-supported approximation, not a recoverable pair-ID list. No individual pair can be labeled definitely seen. Per-style exposure is also unknown; five examples per style is only the balanced expectation, not an observed count.

The inference-only probe selects four known **train-split** identities (`0000000`, `0000055`, `0000514`, `0001021`) × all five styles = 20 pairs. These span a typical hand, the largest nail-mask share, the smallest share, and a crop with larger potential concentration. Their identities are absent from validation. Their individual exposure during steps 1–25 remains **UNKNOWN**. All five styles, including the three failures and red/black controls, are represented.

## Edit-signal measurement

[`scripts/diagnose_n001_signal.py`](../../scripts/diagnose_n001_signal.py) read the immutable ZIP, compared each train target RGB pixel against its reference, and counted hard-mask pixels. It rejected any change outside the masks. Full [80-pair measurements](NAILS-001-step025-signal.json) are retained; the working output and crop figures are private under `data/nails/work/NAILS-001-step025-diagnostic/`.

| 512×512 train pairs | Mean | Median | Min | Max |
| --- | ---: | ---: | ---: | ---: |
| Nail-mask area (% of image) | 0.793% | 0.719% | 0.602% | 1.194% |
| Any RGB target change (% of image) | 0.793% | 0.719% | 0.602% | 1.194% |
| Possible existing nail crop area (% of image) | 44.26% | 44.05% | 26.55% | 59.87% |
| Mask share *within* that crop | 1.841% | 1.758% | 1.334% | 2.609% |

There are five masks per image; connected nail islands average 21.4×23.3 pixels (median 21×23). The approved renderer changes effectively every mask pixel for all styles, including French Tip and Pink Ombre. That whole-mask change percentage **overstates their distinctive structure**: the French Tip's fully white core, calculated from the approved landmark-aligned renderer boundary, averages only **0.158% of the entire image** (0.115–0.225%). Pink Ombre's gradient is expressed across nails only about 23 pixels high, with no separate mask-weighted loss.

Training images contain the full photographed hand against a mostly light background. The app's current `crop_nails` computes a bounding box around all nails plus 20%/24-pixel padding and `prepare_model_crop` fits it into 512 without stretching (`backend/app/nails/geometry.py:110-128`). That option **was not used for DATA-N001 training**. Applying its geometry to the existing masks would increase mask concentration from 0.79% to 1.84% on average, about 2.3×, with a mean 1.4× linear upscale. The nails' spread across fingers means this is a modest increase, not proof that a crop change alone solves style learning. Diagnostic figures `data/nails/work/NAILS-001-step025-diagnostic/crop-0000000.png` and `crop-0001549.png` do not alter DATA-N001.

## Inference status and decision

The existing held-out review found Base-like red/black, vivid magenta Nude Pink, failed French Tip structure, and flat Pink Ombre; adapter per-nail RGB error improved over Base in only 6/20 validation pairs. The Supervisor subsequently ran the inference-only Kaggle probe successfully on 20 train-split pairs. The returned ZIP, all 40 generated output hashes, Base/adapter nail-only errors and 20 composites passed independent checks. The adapter moved closer on 12/20 train-split pairs, mean nail RGB MAE 49.55 → 46.32, yet Nude Pink and French Tip worsened by style mean and visual review found no reliable French tips or ombre. See the [full train-split review](NAILS-001-step025-trainset-review.md) and [per-pair QA](NAILS-001-step025-trainset-qa.json). The previous held-out review's letter “D” described failed style quality under an earlier decision scheme; it did **not** establish PATH D (wrong training configuration) in the Supervisor's current A/B/C/D diagnostic scheme.

The exact prepared handoff is the private `data/nails/work/NAILS-001-step025-diagnostic-bundle.zip`, SHA-256 `1a0996b3022919bf38016f0e29de37bc28952c8a7c539f9d1f08e99ee626c13f` (64,456,773 bytes). It embeds the approved DATA-N001 archive, byte-identical step-25 checkpoint, `scripts/nails001_trainset_probe.py`, and `RUN.txt`. ZIP CRC and embedded hashes passed. A local `--preflight-only` check verified all 20 selected reference/target/mask/caption paths and hashes. On Kaggle it will generate Base and adapter images with the held-out evaluation's seed 1977, 20 steps, guidance 4.0, prompt, 512 input, and inward-feathered nail-only composite; save five-panel sheets; report nail-only target RGB error; and package output. The script has no training path.

**Current A/B/C/D classification: undetermined because exact first-25 sample exposure was not logged.** The observed train-split failure is C-like, but it does not prove the checkpoint failed a pair it definitely saw. A/B cannot be established from these images, and no PATH D configuration error was found. The small nail signal and only 25 of 80 possible first-pass examples remain competing explanations. Do not continue training or change DATA-N001 yet.

**Exact next Supervisor action:** Review the five [train-split contact sheets](NAILS-001-step025-trainset-review.md) and decide whether to authorize a small, logged comparison of current full-hand input against a stronger nail-focused training representation. Preserve the approved DATA-N001 and step-25 evidence. No training cell should be run under this diagnostic task.

## Kaggle handoff correction

The Supervisor attached the diagnostic ZIP as a Kaggle input. Original Cell 1 raised `StopIteration` while searching for the wrapper ZIP. A first correction then raised `FileNotFoundError` for `DATA-N001-final.zip`. The supplied Kaggle file list proves Kaggle unpacked **both** the wrapper and the nested approved DATA-N001 ZIP into a `DATA-N001-final/` folder. This is an input packaging failure before inference; target files are visible, but the byte-identical approved dataset archive is not. Do not rebuild that approved archive from extracted files or bypass its hash gate.

The verified recovery artifact is `data/nails/work/NAILS-001-step025-diagnostic-upload.bin`, an exact byte-for-byte copy of the original wrapper ZIP (64,456,773 bytes, SHA-256 `1a0996b3022919bf38016f0e29de37bc28952c8a7c539f9d1f08e99ee626c13f`). ZIP CRC and nested DATA-N001 SHA-256 `d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb` passed. The earlier project pilot used the same `.bin` upload convention to prevent Kaggle Dataset extraction. The [new Cell 1](../guides/nails001-step025-inference-only.md) locates this `.bin`, verifies it, extracts it under `/kaggle/working`, then checks the original dataset and checkpoint hashes; its `.bin` input layout passed local simulation. The old ZIP input can remain attached but must not be used. The bundle's embedded `RUN.txt` has the original ZIP search and is superseded by the linked guide.




