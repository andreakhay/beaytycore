# NAILS-001 step-25 train-split inference review — 2026-09-27

**Status: VERIFIED inference and artifact integrity; visual quality FAILED; exact prior sample exposure UNKNOWN.** This was an inference-only diagnostic. No training was resumed and app inference remains disconnected.

## Provenance and checks

The Supervisor's Kaggle probe returned 0 after generating 20 pairs. The downloaded `NAILS-001-step025-trainset-probe-results.zip` is retained privately at `data/nails/work/` and has SHA-256 `b8a3e052c8256c6cd4dee9575efc87491a8e9088d7d7b538ac6db50a7535c48f`. `python scripts/verify_n001_trainset_probe.py` passed ZIP CRC, exact 81-member layout, approved DATA-N001 SHA-256 `d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb`, checkpoint SHA-256 `34bf82238dfcc8e6365cd9fa6b63d36700312780f2e396dc6d91f7cc3f829c91`, pinned Base revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, manifest train split, each source/target/mask hash and caption, all 40 output hashes and nail-region MAEs, and all 20 compositing results. It confirmed **zero changed pixels outside the hard nail masks** in every final composite. Full [per-pair metrics](NAILS-001-step025-trainset-qa.json) are retained.

The four train-only identities are `0000000`, `0000055`, `0000514`, `0001021`, each with five styles. Evaluation used the same caption and settings as held-out evaluation: seed 1977, 20 inference steps, guidance 4.0, 512×512 reference, and the same inward-feathered nail compositor. Kaggle metadata reports Tesla T4, Torch 2.10.0+cu128, Diffusers 0.39.0.dev0. These pairs are **train-split examples, not confirmed-seen examples**: the first 25 sampler IDs were never logged and cannot be recovered. The probe must not be described as a demonstrated memorization/fitting test of any particular seen pair.

## Visual evidence

Each row of the retained style sheets is one identity; columns are **Original | Approved Target | Base | Step-25 Adapter | Final Nail-Only Composite**. Identity order is `0000000`, `0000055`, `0000514`, `0001021`.

- [Classic Red contact sheet](NAILS-001-step025-trainset-review/classic_red.jpg)
- [Nude Pink contact sheet](NAILS-001-step025-trainset-review/nude_pink.jpg)
- [Glossy Black contact sheet](NAILS-001-step025-trainset-review/glossy_black.jpg)
- [French Tip contact sheet](NAILS-001-step025-trainset-review/french_tip.jpg)
- [Pink Ombre contact sheet](NAILS-001-step025-trainset-review/pink_ombre.jpg)

| Style | Adapter closer by nail-mask RGB MAE | Base mean / Adapter mean MAE | Visual finding |
| --- | ---: | ---: | --- |
| Classic Red | 3/4 | 61.91 / 56.97 | Red appears, but Base already produces similar deep glossy red. Adapter does not reproduce the approved lighter target tone. |
| Nude Pink | 1/4 | 30.98 / 42.90 | Both models often produce saturated magenta; adapter is visibly farther from the approved muted nude tone on several hands. |
| Glossy Black | 3/4 | 67.01 / 47.38 | Recognizable glossy black. Adapter is numerically closer, but Base already delivers comparable style and sheen. This is the clearest quantitative adapter movement. |
| French Tip | 2/4 | 45.96 / 48.69 | No consistent natural base with thin white tips. Outputs include blue/gray full-nail polish, nail extension, and patterned polish; the final mask clips geometry but cannot restore the intended design. |
| Pink Ombre | 3/4 | 41.90 / 35.65 | Some pink color movement, but gradients are inconsistent, often flat/too saturated or reversed relative to approved targets. Base sometimes looks more plausible. |

Across all 20 train-split pairs, adapter is closer on 12 and mean nail RGB MAE changes **49.55 → 46.32**. RGB error is a narrow pixel metric against deterministic targets; it does not establish acceptable style structure. The improvement is concentrated in black and some red/ombre cases, while Nude Pink and French Tip worsen. The previously reviewed **held-out** result improved in only 6/20 comparisons and failed the same three styles. This train-versus-validation difference is insufficient to diagnose overfitting because sample exposure and output quality remain unclear.

Raw Base and adapter generations frequently invent rings/bracelets, alter nail length, and remodel fingers or hand pose. The approved target never contains those additions. The final compositor restores the original outside-mask hand, skin, jewelry and background exactly; it does not make an incorrect generated nail design correct. The dark solid colors show model-generated specular highlights, but those highlights already appear in Base results and do not prove the LoRA learned the renderer's appearance. No useful French Tip structure or reliable pink gradient was observed on these four train-split identities.

## Diagnosis and decision

The separate [code/data audit](NAILS-001-step025-diagnostic.md) found a correct static image-edit path: target, same-stem reference control, and edit caption flow into pinned FLUX.2 Klein training. No reference/target swap, text-to-image-only training, validation leakage or caption mismatch was found. It did not capture runtime tensors. Masks did **not** weight the loss. Nail masks and actual changed target pixels average only **0.793%** of the 512×512 training image; the distinctive French white-tip core averages **0.158%**. Full-hand crop scale and unweighted whole-image loss are plausible causes of weak local style learning, alongside only 25/80 optimization steps. The current evidence does not isolate their causal contributions.

**A/B/C/D: a definitive letter is not supported.** A and B require positive fitting evidence on samples definitely seen, which is unavailable. C requires proving failure on samples definitely seen, also unavailable. D is not supported by the inspected config/loader. The observed behavior is **C-like at the train-split level**: the failed styles remain wrong even on training identities, and Base often equals or exceeds the adapter. That is a reason to **stop rather than blindly continue this checkpoint**, not proof that more steps cannot help.

**Next recommended action:** The Supervisor should review these five sheets and authorize a bounded, logged representation test before more GPU training. Keep the approved DATA-N001 unchanged. A next experimental run should record per-step pair IDs and run a small comparison of the current full-hand input against a nail-focused crop/weighted local signal on the *same train-only identities*, with fixed held-out settings and checkpoints. The current cropper's geometry would increase mask share only from 0.79% to about 1.84% on average, so a crop alone should not be assumed sufficient. Specify the comparison before running it; no training or new dataset was started in this diagnostic.
