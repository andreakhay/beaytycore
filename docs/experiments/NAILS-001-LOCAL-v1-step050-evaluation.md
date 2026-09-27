# NAILS-001-LOCAL-v1 step-50 held-out evaluation

**Classification: PARTIAL, EXPERIMENTAL. Five-style quality gate FAILED at step 50.** This is a real FLUX.2 Klein Base edit-LoRA checkpoint, but it is not approved for application inference. The four validation identities were unseen in training. The approved DATA-N001, Hair, Makeup and existing nail-only compositor remain unchanged.

## Artifact integrity and run

- Supervisor evidence ZIP: `D:/Downloads/NAILS-001-LOCAL-v1-step050-evidence.zip`; SHA-256 `cab51d21acfdfed03b095545de2a692693b0e4567b68708f2955baf195ad39b7` (93,617,450 bytes).
- Separate evaluation ZIP: `D:/Downloads/NAILS-001-LOCAL-v1-step050-evaluation.zip`; SHA-256 `a0c7ec088bc648cd50dd6f4329b8f80eb76efe42764f0ff89a9cb010aa31566c` (8,757,873 bytes). It is byte-identical to the evaluation member inside the evidence ZIP.
- Approved DATA-N001 SHA-256 `d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb`; localized derivative SHA-256 `d7440f1cc1a8987c48235fed36f8ff23581c17719b219fc2a7e600ad867bcf90`. Localized training has 340 pairs across 16 identities; 90 validation pairs across 4 separate identities. Training mean nail area was 11.252%, versus 0.793% in the original full-hand training images.
- Base: `black-forest-labs/FLUX.2-klein-base-4B` revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`. AI Toolkit commit `a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7` (package metadata 0.13.19). Tesla T4, CUDA runtime 12.8, Torch `2.10.0+cu128`, Diffusers `0.39.0.dev0`, Transformers 5.5.3, Accelerate 1.13.0, PEFT 0.18.1, bitsandbytes 0.50.2.
- Config: 512×512 paired edit with reference `control_path`, BF16, batch 1, gradient accumulation 1, AdamW8bit, learning rate 1e-4, seed 1977, linear LoRA rank/alpha 16/16 and conv rank/alpha 8/8. Config SHA-256 `f0e6116a01ea51e7b319d889050005d59d7fac7824702ed0b3147db2f909d695`.
- Training exited 0 after **50 steps**; 50/50 distinct train-split pair IDs were traced. The checkpoint safetensors header independently identifies step 50 and `flux2_klein_4b`. The finite log ends with loss `0.06529`; loss is not a style-quality verdict. Wall time including load: 1,793.1 seconds (29.9 minutes); observed whole-GPU peak: 13,531 MiB.
- Experimental checkpoint SHA-256 `5bff16c67e0014c78a6d938813347685f914f8a608d76407b10f5b54b7a0eb1f`; optimizer SHA-256 `0959ce2f726e3c5c8b76e106f4c3278e4692fd8b028f2b7216f2199b382f51ec`.

The [independent verification record](NAILS-001-LOCAL-v1-step050-qa.json) checks ZIP CRC, all packaged file hashes, checkpoint header, trace-to-manifest identity/style/finger mapping, validation identity separation, 40 generated output hashes, all 20 mask-region MAEs, and zero changed full-hand pixels outside each original nail mask. The separate evidence and evaluation archives match. Exact train exposure by style: Classic Red **7**, Nude Pink **9**, Glossy Black **11**, French Tip **7**, Pink Ombre **16**. Thus step 50 covers only 14.7% of the 340 train pairs and is not one meaningful pass.

## Held-out comparison

The same 20 inference steps, guidance 4.0, seed 1977, reference crop and style instruction were used for Base and adapter. Evaluation covers the index fingernail for each of four held-out identities, all five styles. Numbers below are mean RGB absolute error **inside the approved localized nail mask**; lower is closer to the approved deterministic target. They complement, but do not replace, visual judgment.

| Style | Base MAE | LOCAL step-50 MAE | Adapter better hands | Visual review |
| --- | ---: | ---: | ---: | --- |
| [Classic Red](NAILS-001-LOCAL-v1-step050-review/classic_red.jpg) | 48.424 | 47.377 | 2/4 | Recognizable red and highlights, but similar to Base; target match inconsistent. |
| [Nude Pink](NAILS-001-LOCAL-v1-step050-review/nude_pink.jpg) | 30.604 | 48.194 | 0/4 | Dark mauve/brown or purple, with blotchy or missing coverage; fails muted nude-pink tone. |
| [Glossy Black](NAILS-001-LOCAL-v1-step050-review/glossy_black.jpg) | 46.806 | 36.271 | 4/4 | Black is recognizable and numerically closer to target, though Base already makes convincing glossy black. |
| [French Tip](NAILS-001-LOCAL-v1-step050-review/french_tip.jpg) | 38.527 | 58.995 | 0/4 | Some white areas appear, but tip width/placement is unreliable and the nail bed turns brown or dark; fails natural thin-tip requirement. |
| [Pink Ombre](NAILS-001-LOCAL-v1-step050-review/pink_ombre.jpg) | 44.773 | 35.032 | 4/4 | Numerically closer than Base, but often vivid magenta, blotchy, or directionally wrong; fails consistent soft base-to-tip gradient. |

The raw adapter crop has mean outside-nail MAE **2.997** against its input reference, versus **10.218** for Base. This is evidence that local training improved raw fingertip preservation. Raw adapter crops still sometimes alter cuticle tone or blur the nail boundary. The unchanged final nail-only compositor preserved exact original pixels outside the selected nail region on all 20 full-hand previews, including skin, pose, jewelry and background. Each preview edits one nail only; all-finger reconstruction was not evaluated in this run. Generated shading is soft and often blurred; the approved targets themselves contain enlarged, somewhat blocky nail edges.

## Decision and next action

**PARTIAL:** localization increased the training signal and improved raw preservation; Glossy Black and Pink Ombre moved closer to approved target pixels. Those gains do not establish correct Ombre structure, while the two other hard styles became worse than Base on all four unseen hands. The adapter does **not** generalize reliably across the five requested styles at step 50. Do not deploy or connect it to `/nails`.

Because only 7 French Tip and 9 Nude Pink pairs were seen, step 50 is too early to conclude that localized FLUX editing cannot learn them. One bounded continuation to about **170 total steps** (half of one 340-pair pass), followed by the identical held-out evaluation, is justified **only after** verifying the pinned AI Toolkit resumes this checkpoint and optimizer without resetting its step or corrupting the exact sample trace. The [read-only resume audit cell](../guides/nails001-local-v1-resume-audit.md) packages the pinned source needed for that check. Preserve the step-50 checkpoint unchanged. If the hard styles are still wrong at that checkpoint, stop FLUX retraining and move to the fallback architecture; do not extend blindly to hundreds more steps. No continuation has been launched or approved as a successful model result.
