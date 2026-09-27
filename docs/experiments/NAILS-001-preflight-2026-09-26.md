# NAILS-001 pilot preflight and Kaggle handoff — 2026-09-26

**Evidence status: VERIFIED for local archive/config checks; NEEDS VERIFICATION for GPU training and model quality.** No NAILS-001 training step or held-out model inference ran in this task. Real Nails application inference remains disconnected.

## Immutable input audit

The approved `data/nails/work/DATA-N001-final.zip` is 22,460,375 bytes and has SHA-256 `d37b68bc3e06c6ea1b1b013424dd813aafbef83db222cf9223e229d33ad105bb`, matching the DATA-N001 construction record. Its ZIP CRC passes. Its manifest contains 100 reviewed ACCEPT pairs: 16 train-only identities × five styles (80 pairs) and four validation-only identities × five styles (20 pairs). Train identities and validation identities are disjoint. Captions, masks, references and targets are hashed in the manifest.

The previously approved `data/nails/work/NAILS-001-pilot-bundle.zip` is 22,473,729 bytes with SHA-256 `6c75cec008f5175aeeeaa5e9e611c8de59e7a12d3c5177cbddfa32dd956b1d6c`. Its CRC passes. Every one of the 405 files under its `data_n001/` prefix matches the approved DATA-N001 archive byte for byte. Its `RUN.txt` pins AI Toolkit commit `a8dfcf7d7e2b38ccc7b2fb68ece9c6358e61e7a7` and FLUX.2 Klein Base revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`. Its config specifies a 75-step edit LoRA with saves at 25-step intervals and the training `target/` plus `reference/` control path. These values agree with the previous NAILS-001 plan. There is no source dataset or Base revision contradiction.

The old handoff assumed a correctly installed toolkit and authenticated model access. Its runner omitted dependency setup, complete runtime evidence, and observed GPU memory. Its evaluator produced one checkpoint's Original / Mask / Model Crop / Final sheet without the reviewed Target or a Base comparison. Running all 75 steps before inspecting step 25 would also spend GPU time beyond the first quality decision. These are handoff gaps, not evidence that the approved data is wrong.

## Bounded pilot handoff

`scripts/package_n001_pilot_v2.py` produced `data/nails/work/NAILS-001-pilot-v2.zip` without modifying either approved archive. SHA-256: `5181220b6999cfdb52e87f00b0330767adee0f940669e271a5517b58a98b634a`; size: 22,392,334 bytes; ZIP CRC passed. `NAILS-001-pilot-v2-upload.bin` is a byte-identical upload copy with the same hash; the `.bin` suffix keeps Kaggle Dataset upload from auto-extracting the outer ZIP. The nested `DATA-N001-final.zip` retains the exact approved SHA-256 above. `RUN.txt` contains the Kaggle cells; `scripts/nails001_kaggle_pilot.py` is the included runner.

The new config preserves the existing FLUX.2 Klein Base, AI Toolkit commit, LoRA linear rank/alpha 16/16 and conv rank/alpha 8/8, 512-pixel paired edit control path, batch size one, BF16 training, FP16 save, `adamw8bit`, learning rate `1e-4`, flow matching, gradient checkpointing, quantization and low-VRAM mode. It explicitly sets gradient accumulation to one. The first run stops at step 25 and saves at step 25; this is a deliberate shorter gate than the old unrun 75-step bundle. The runner seeds Python, NumPy and Torch to 1977 before entering AI Toolkit and records the command. Fixed validation inference uses seed 1977, 20 steps and guidance 4.0. Any toolkit-internal reseeding must be checked from its Kaggle logs; no training reproducibility claim is made before the run.

Before training, the runner verifies the exact approved archive hash and CRC, every manifest reference/target/mask hash, ACCEPT status, captions, 16/4 split and balanced five-style coverage. Only `data_n001/train/target` and matching train references are passed to AI Toolkit. It pins the toolkit commit, constrains pip to Kaggle's installed Torch/CUDA stack, checks that Torch/CUDA remain unchanged after installation, resolves the pinned Base revision, and records package versions, GPU, CUDA, Base weight hash and command. It captures train log, wall clock, observed whole-GPU peak MiB, finite losses, checkpoint and optimizer hashes. After successful training it generates Base and adapter images for all 20 held-out pairs using identical prompts/settings, saves nail-only composites, and creates Original / Target / Base / Adapter Crop / Final contact sheets. The output ZIP retains training config/logs, checkpoint/optimizer, hashes and all evaluation records. All results remain `PENDING_HUMAN_REVIEW`.

## Checks run locally

- `python -m py_compile scripts/nails001_kaggle_pilot.py scripts/package_n001_pilot_v2.py` — passed.
- `python scripts/package_n001_pilot_v2.py --dataset data/nails/work/DATA-N001-candidates-v2 --archive data/nails/work/DATA-N001-final.zip --output data/nails/work/NAILS-001-pilot-v2.zip` — passed, with immutable data hash and CRC checks.
- Extracted the new bundle locally and ran `python nails001_kaggle_pilot.py --phase prepare --root <extracted-directory>` — passed. It reported 100 pairs, the frozen 16/4 identity split, and 16 train plus four validation examples per style. This was a CPU data/config check only.
- `python -m pytest backend/tests/test_nails_data.py -q` — one test passed. The temporary extraction used for the local preparation check was removed after verification.

Local Torch is `2.10.0+cpu`; CUDA is unavailable and `nvidia-smi` and Kaggle CLI/credentials are absent. The available Kaggle browser page showed Sign In, not an authenticated notebook. Therefore the GPU environment, training duration, peak memory, checkpoint hash, held-out style/localization/preservation/generalization quality, and continuation decision remain **UNKNOWN**. No model file has been trained or evaluated here.

## Supervisor action

In a private authenticated Kaggle notebook, enable T4 GPU and Internet, attach a private Dataset containing `NAILS-001-pilot-v2-upload.bin`, and run the two cells in its `RUN.txt`. If Base access requires it, attach an `HF_TOKEN` Kaggle secret. Download `NAILS-001-pilot-step025-evidence.zip` and return it for full-resolution human review. Do not run a continuation or connect application inference until the step-25 evaluation is reviewed. If the Kaggle cell fails, retain the complete `/kaggle/working/nails001/` output and report its error/logs; no simulated checkpoint can substitute.
