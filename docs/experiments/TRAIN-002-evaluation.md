# TRAIN-002 held-out comparison: preliminary review

Status: **evaluation artifacts verified; visual review preliminary; T4 adapter switching reported PASS**. The Supervisor supplied `D:/Downloads/train002_evaluation.zip` and `D:/Downloads/reference_base_adapter_target (1).jpg` and reported that the comparison looks good. Codex inspected the full-resolution sheet and archive without running GPU inference.

## Artifact checks

The evaluation ZIP is 6,519,797 bytes, SHA-256 `6dd860b019ac3476143129a2ed43d3fad220517dd8d53b67b7f4f024b2d7631f`, with 25 members and no CRC errors. It contains exactly ten Base outputs, ten adapter outputs, `metadata.json` with 20 records, and `reference_base_adapter_target.jpg`. Every output PNG decodes and matches its metadata SHA-256. The separate downloaded sheet is byte-identical to the ZIP sheet. Evaluation metadata identifies the trained checkpoint hash `59d527217a68139bc2aaa4eedbfcd2d5789ef115f8ecb924410eea24a952939b`. The evaluation manifest still says `visual_review: PENDING` because this local review has not changed the original archive.

The sheet columns are source, Base, TRAIN-002, and paired target, with one held-out direction for each of the ten classes. Both inference paths used the same input, prompt, seed, resolution, step count, and guidance as specified in `notebooks/train002_kaggle.py`.

## Visual observations

| Requested style | Preliminary observation |
| --- | --- |
| `bun` | Bun is clear; identity and scene are broadly recognizable. Base also made a bun. |
| `curtain_hair` | TRAIN-002 produced long dark bangs and curls rather than the paired target's shorter parted curtain shape. Identity/appearance drift is visible. **Needs another check before enabling.** |
| `perm_curls` | Clear dense curls and recognizable pose/scene; hair color and some facial appearance differ. |
| `pixie_cut` | Short pixie shape is clear and close to target; Base is already similar. |
| `pompadour_undercut` | TRAIN-002 exaggerates the height into a block-like top compared with the more natural target. **Needs another check before enabling.** |
| `ponytail` | Ponytail is visible and scene is stable; Base is already similar. |
| `shag_hair` | Choppy layered shape is visible and closer to the requested look; some appearance drift. |
| `shoulder_length_hair` | Clear length increase with broadly stable identity and background; Base is already similar. |
| `side_part_undercut` | TRAIN-002 output has a high swept top, but the side part is not clear and differs from the paired target. **Needs another check before enabling.** |
| `wavy_hair` | Wavy/curly target is visible; Base is already similar. |

This is a useful proof that the adapter can be loaded for evaluation and produces varied hairstyle edits. It is not evidence that TRAIN-002 consistently beats the Base model: Base already follows several of these prompts, and there is only one held-out direction per style in the sheet. The underlying DATA-002 counterparts were accepted structurally without visual review. No new style is enabled by this assessment.

## Runtime gate

The derived deployment bundle passed metadata/hash checks, and the Supervisor's T4 TRAIN-001 → TRAIN-002 → TRAIN-001 smoke passed with identical first/third output hashes; see [switch smoke](TRAIN-002-switch-smoke.md). Preserve TRAIN-001 as the live fallback. Recheck `curtain_hair`, `pompadour_undercut`, and `side_part_undercut` before treating them as supported. No TRAIN-002 style has been enabled in the live application.
