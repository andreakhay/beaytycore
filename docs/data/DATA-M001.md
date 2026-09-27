# DATA-M001 dataset audit and controlled target construction

Status: IN PROGRESS. Evidence status: VERIFIED for archive structure, a visual source shortlist, and frozen source metadata; GPU target generation has NOT STARTED. Date: 2026-09-25. Stage 3 below supersedes earlier provisional dataset budgets and strategies. MAKEUP-001 training remains unauthorized.

## Scope and decisive finding

The intended first MAKEUP-001 remains one conditional Makeup LoRA covering approximately ten finalized styles. Natural, Soft Glam, and Smoky were only the Base pilot. Hair assets, its registry, and its inference path are outside this work.

The [FFHQ-Makeup paper](https://arxiv.org/pdf/2508.03241) says each FFHQ identity receives **five randomly selected** looks from a bank of 2,257 curated residuals (section 3.3). Therefore `makeup_01` through `makeup_05` are five per-identity positions, not five global classes. The current archive offers no documented mapping from a suffix to a project style. Training a text-conditioned ten-style LoRA from suffixes alone would teach incorrect labels.

## A. FFHQ-Makeup source audit

| Property | Evidence and status |
| --- | --- |
| Repository | [`cyberagent/FFHQ-Makeup`](https://huggingface.co/datasets/cyberagent/FFHQ-Makeup), revision `25955d8cb70e97b00f3ee9eacffabc9d3fda81a7` is the inspected repository tree. It contains `FFHQ-Makeup.zip` and a README. Archive bytes were **not** available locally. |
| Claimed scale | Card and paper report 18,000 identities, one bare plus five makeup images each, hence 90,000 edit pairs and 108,000 image files. **Reported, not archive verified.** |
| Naming and dimensions | Card reports 512 by 512 JPEGs. Former repository preview paths show names like `002386_bare.jpg` and `002386_makeup_01.jpg` through `_05.jpg`. The actual ZIP directory hierarchy, image dimensions, and completeness remain unverified. |
| Pairing | Paper describes transfer of five makeup references onto the same FFHQ target identity. Shared numeric prefix appears to identify the same source. **Method and examples support pairing, but selected ZIP pairs still need visual review.** |
| Split | A split by numeric FFHQ identity ID is practical if ZIP inspection confirms unique IDs. All variants of an ID must stay in one split. Cross-ID near duplicates and original FFHQ image reuse need checks. Do not trust pair-level random splitting. |
| Style semantics | Five looks are sampled independently for each identity from 2,257 references originally drawn from MT and LADN. No global class labels are documented. |
| License | Hugging Face declares `cc-by-nc-sa-4.0` and says it inherits FFHQ terms. [NVIDIA FFHQ](https://github.com/NVlabs/ffhq-dataset) describes mixed per-photo Flickr licenses plus dataset-level CC BY-NC-SA 4.0. Noncommercial use, attribution, change notices, and share alike for distributed adaptations must be handled. The makeup reference photos' item-level licenses are not documented in the card or paper, so clearance for redistributed derived pairs is unresolved. This is a rights risk, not a finding of infringement. |
| Practical size | Hugging Face reports about 3.82 GB compressed. Downloading once for a CPU audit is plausible on Kaggle or a local machine with enough storage, but transfer time and uncompressed size are unmeasured. The disabled dataset viewer prevents selective hosted inspection. |
| Bias and quality | Card warns of demographic limits and occasional off-face artifacts. The paper reports manual filtering. These are claims, not a substitute for our per-pair acceptance review. |

The historic preview deletion [lists several complete six-file groups](https://huggingface.co/datasets/cyberagent/FFHQ-Makeup/commit/4865ef258539c34fe26d3502b1a3f324f9094da1). It supports the naming pattern, not the complete ZIP inventory. The authors' [project examples](https://yangxingchao.github.io/FFHQ-Makeup-page/) show varied cosmetics across identities, but cannot establish which specific ZIP variant represents which project label. No local contact sheet was produced because the ZIP is not present and outbound command-line access to Hugging Face failed. Do not report this visual audit as complete.

## B. Ten-style compatibility

Here `NONE` means no **reliable, directly usable conditional class mapping from the published dataset as-is**, not proof that no individual image depicts the look. `PARTIAL` means a visible example or broad source appearance suggests potentially useful individual pairs, but each pair still needs human relabeling and quality review. There is no `DIRECT` class today.

| Candidate project style | Support | Evidence and limitation |
| --- | --- | --- |
| Natural Makeup | NONE | No named natural class or suffix rule. The subtle pilot showed Natural and Soft can overlap. |
| No-Makeup Makeup | NONE | No named near-invisible class; distinction from Natural cannot be established from card or paper. |
| Soft Glam | NONE | No named soft glam class; generic cosmetics are insufficient evidence. |
| Smoky Glam | NONE | No named smoky eye class or variant mapping. |
| Dewy Peach | NONE | No controlled peach color and dewy finish labels. |
| Rosy Pink | PARTIAL | Authors' illustrative examples show pink or magenta color, but not a controlled coordinated rosy look or ZIP labels. |
| Bronze / Golden Glam | NONE | No verified bronze/gold class or finish. |
| Matte Nude | NONE | No verified matte finish or nude palette labels. |
| Classic Red Lip | PARTIAL | Authors' examples show a bold red lip, but the rest of the look and actual archive membership need review. |
| Bold Evening Glam | PARTIAL | Authors' examples show bold colorful cosmetics; no consistent evening class or reliable suffix label. |

This matrix is deliberately conservative. A sampled contact sheet of actual ZIP files could upgrade or downgrade individual rows. It cannot make `makeup_01` a global class because the authors state the reference selection was random. Natural versus No-Makeup, and Smoky versus Bold Evening, are possible overlaps to test, not grounds to merge them yet. The source's blue and magenta statement looks may not fit the current taxonomy; record them as `other_look` rather than forcing a label.

## C. Strategy comparison and recommendation

| Strategy | Fit | Decision |
| --- | --- | --- |
| A. Use the five existing variants directly as classes | Fast download and genuine same-identity edits, but five random reference positions are not ten semantic classes. | Reject **as-is**. Manual labels would turn it into B. |
| B. Hybrid reviewed FFHQ pairs plus generated gaps | Uses stronger existing pairs where visual labels, rights, and preservation pass; generates only missing style-by-identity targets. | **Recommended provisional strategy**, subject to ZIP visual and provenance audit. |
| C. Generate all ten targets from cleared bare portraits | Gives balanced instructions but inherits the Base pilot's identity and geometry drift; 140 outputs at roughly 73 seconds each would take about 2.8 hours before load, retries, and training. | Fallback if B cannot yield sufficient class-balanced pairs and source rights are cleared. |
| D. Another source | [BeautyBank BMS](https://huggingface.co/datasets/lulululululululululu/Bare-Makeup-Synthesis-Dataset) lists 319,516 makeup images at 512 pixels but requires separate FFHQ bare images and about 125 GB of multipart downloads. It also lacks our ten labels. | Not a better deadline path based on the current source cards. Revisit only if FFHQ-Makeup audit fails. |

Do not approve FFHQ-Makeup for training until the archive and sample labels are inspected. The paper's use of MT/LADN references and the absence of item-level reference rights require a documented project decision on derivative use and distribution. This is especially important before publishing images, pairs, or a checkpoint.

## D. Minimum practical design

Proposed floor: **14 distinct source identities**, 10 train and 4 held-out validation. Ten candidate styles per identity would yield 100 train and 40 validation edit pairs, 140 total, if every target is accepted. This is a small capstone demonstration, not evidence of broad generalization. The four validation identities support the previously chosen minimum four Base-versus-LoRA comparisons for each of ten styles (40 comparisons), rather than the obsolete 12-comparison three-style gate. If source curation is easy, 16 train plus 4 validation identities (200 pairs) is preferable; do not inflate to this without deadline and GPU budget review.

For a hybrid set, target one accepted target per identity and style. Existing FFHQ pairs can fill cells only after explicit `ACCEPT` with a project style label. If a source identity lacks an accepted direct pair for a style, generate exactly that missing cell from its bare portrait. Thus synthetic workload is `140 minus accepted existing cells` at the floor, initially capped at **two identities times ten candidate styles = 20** for a prompt and taxonomy pilot. Do not assume all 140 are generated. Style balance, not raw archive size, controls finalization. Reject a style that cannot obtain enough distinct, accepted identities, then request taxonomy review rather than silently shrinking the model.

At 512 pixels, 140 RGB images are roughly 110 MB uncompressed pixel data, plus 14 sources; compressed JPG or PNG storage is content-dependent and must be measured, not guessed. The 3.82 GB source ZIP should remain a separate pinned input. The output manifest and small contact sheets should be saved in a durable Kaggle output or downloaded before closing a session.

Validation must be identity-disjoint by source FFHQ ID, including all five existing variants and all generated derivatives. Audit exact source SHA-256 and perceptual near duplicates across identity IDs. The project must not reuse the three Pinterest Base-pilot portraits as training data.

## E. Namespace and manifest contract

Proposed folder layout, independent of DATA-001/002:

```text
docs/data/DATA-M001.md
data/makeup/DATA-M001/
  source_manifest.json
  taxonomy.json
  selection_manifest.json
  reviews.json
  final_manifest.json
  sources/<identity_id>/bare.jpg
  targets/<identity_id>/<style_id>.png
  metadata/<identity_id>/<style_id>.json
  review_sheets/
  pairs/train/
  pairs/validation/
```

Keep large images and upstream ZIP out of Git; store frozen manifests, archive digest, review decisions, and a small representative sheet as appropriate. The archive is pinned by repository ID, commit, filename, SHA-256, card/license snapshot, and retrieval date. Each identity record has `identity_id`, original FFHQ ID, source member, source SHA-256, image dimensions, upstream photo author/license URL if resolved, and split. Each target cell has `style_id`, `target_origin` (`ffhq_makeup` or `flux_base_synthetic`), original ZIP member or exact prompt/model revision/seed/config, target hash, review status (`PENDING`, `ACCEPT`, `REJECT`), reviewer note, and visible drift tags. Final pairs use explicit source and target paths, hashes, split, style ID, caption, and source attribution reference. Reject incomplete provenance, duplicate hashes, missing source/target, unknown style IDs, or a validation ID in training. The ten style IDs remain in the Makeup namespace defined by `backend/app/makeup_styles.py`; no Hair registry entry is added.

The DATA-002 [manifest](DATA-002-manifest.json) and [generator](../../notebooks/data002_generate_kaggle.py) were read for generic provenance, split, retry, and contact-sheet patterns only. Hair-specific neighbor graphs, captions, adapter fields, and scripts are not reused.

## F. Prepared next stage and stopping gate

[`scripts/data_m001_audit.py`](../../scripts/data_m001_audit.py) is a CPU-only ZIP inspector. Given a locally available `FFHQ-Makeup.zip`, it inventories identity groups, missing/duplicate variants, hashes a representative sample, checks sampled dimensions/formats, and writes `ffhq_makeup_audit.json` plus `ffhq_makeup_sample_sheet.jpg`. It never loads a model or assigns suffixes to styles. Its local fixture tests passed. The real archive has not been run through it.

Next, on a CPU session or local machine, download the pinned archive once, record its SHA-256, run the script, and manually classify at least twelve diverse identity rows. Review actual variant positions across multiple identities, pair consistency, off-face changes, and style frequencies. Link selected FFHQ IDs to NVIDIA's per-photo metadata and capture the upstream credit/license. Freeze the source and taxonomy only after review. If synthetic gaps remain, prepare a separate DATA-M001 Kaggle Base runner using the pinned Base, no LoRA, two cleared identities and ten proposed prompts, with per-output sidecars, failure records, full resolution images, and a contact sheet. **Do not run that GPU phase in this task.**

The prepared CPU command for a Kaggle notebook with Internet enabled and this script attached is:

```text
python data_m001_audit.py --download --output /kaggle/working/data_m001_audit --sample-count 12
```

It requires Pillow and `huggingface_hub`, not a GPU. If the ZIP is already attached as a Kaggle Dataset, pass its absolute path instead of `--download`. Save the resulting JSON and sheet as a Kaggle output or download them before ending the session. No dataset archive or portrait is uploaded by this command.

## Open gates

1. Actual ZIP layout, complete identity count, dimensions, and visual pair quality are not yet verified.
2. Style coverage and reliable per-image labels are unknown. No final taxonomy or source selection is approved.
3. Upstream makeup reference rights and the correct treatment of any redistributed derivative images or trained weights need review.
4. A 10-style LoRA trained from only ten identities may underfit or memorize. Its success must be tested on four held-out identities per style against the pinned Base, with identity and facial geometry review.
5. GPU and storage availability for the remaining deadline are not measured here. The 20-output pilot is a gate, not an automatic full run.

## Stage 2: actual archive audit (2026-09-25)

### Runtime and source

The requested Kaggle notebook was not reachable from this task. The same prepared auditor ran on the local **CPU** instead. Python 3.11.5, no `torch`, CUDA, or FLUX import, and no GPU use. The local F drive had about 42.4 GB free before the download. Direct official Hugging Face access worked after bypassing a broken local proxy. The first transfer stalled at 620,785,664 bytes; a resumable direct transfer completed successfully. Its official source was `cyberagent/FFHQ-Makeup`, revision `25955d8cb70e97b00f3ee9eacffabc9d3fda81a7`, file `FFHQ-Makeup.zip`, 3,811,722,185 bytes. SHA-256 `c15fd40199b4d46050dc864eaed647b0ad41921507c2f99cb1cfec2b46922c6a` matches Hugging Face's `X-Linked-ETag` advertised for that pinned file.

The initial script pass found zero identities because the actual ZIP uses nested paths such as `000000/bare.jpg`, while the card's former preview used flattened names such as `002386_bare.jpg`. The parser now supports both layouts. Its regression tests cover the real nested layout. This correction affected only the Makeup audit script and tests.

### Complete inventory and integrity

The corrected pass inspected every recognized archive member and decoded every image. It found **18,370 identity directories**, each with exactly one `bare.jpg` and one each of `makeup_01.jpg` through `makeup_05.jpg`. This is **110,220 images and 91,850 bare-to-makeup pairs**. The paper/card's 18K identities and 90K pairs are rounded descriptions, not the exact ZIP counts. All 110,220 images decoded as JPEG at 512 by 512 pixels. There were zero incomplete groups, unrecognized files, duplicate identity/variant paths, decode failures, or exact duplicate SHA-256 image hashes. This verifies file structure, not cosmetic quality or true identity preservation.

The deterministic sample uses twelve complete IDs evenly spaced across sorted archive identity IDs: `000000`, `003760`, `008845`, `014306`, `020643`, `027775`, `034290`, `041250`, `048564`, `055840`, `062589`, `069936`. The sample covers visibly varied faces and looks but was not selected or labeled by inferred demographics. Some portraits should not be chosen as adult training sources without age and consent review. All 72 full-resolution sampled files are preserved alongside the contact sheet.

Local artifacts, deliberately outside Git: `F:/HAIR/.tmp/data_m001/audit/ffhq_makeup_audit.json`, `F:/HAIR/.tmp/data_m001/audit/ffhq_makeup_sample_sheet.jpg`, three four-row sheet pages, `F:/HAIR/.tmp/data_m001/audit/samples/`, and `F:/HAIR/.tmp/data_m001/audit_run.log`. The JSON includes the archive hash, sample member list, per-sample hashes, decode and duplicate checks, format/dimension counts, and CPU runtime (124.8 seconds). The source ZIP remains separate at `F:/HAIR/.tmp/data_m001/FFHQ-Makeup.zip` and is not in the small artifact bundle.

### Visual findings

Every numeric suffix is **`VARIABLE_RANDOM_LOOK_POSITION`**, not `CONSISTENT_STYLE_CLASS`:

| Position | Contrasting actual sample appearances |
| --- | --- |
| `makeup_01` | `003760` has a vivid magenta lip; `014306` has teal eyeshadow; `027775` is muted; `062589` is nearly natural. |
| `makeup_02` | `003760` has warm blush and nude lips; `014306` has purple eyes; `055840` has dark bluish eyes; `062589` is subtle pink. |
| `makeup_03` | `055840` has a clear red lip; `014306` is comparatively subtle; `069936` has strong purple eyes. |
| `makeup_04` | `027775` has bright blue eyes; `055840` has a red lip; `062589` is near natural. |
| `makeup_05` | `000000` has a purple lip; `014306` has teal eyes; `041250` is restrained; `069936` has dark plum lips. |

The images are structurally paired by source ID and often retain pose and scene composition. Visual preservation is much weaker. Examples: `003760/makeup_02` smooths away facial texture, changes eye and nose structure, and shifts the scene color; `020643/makeup_01` changes facial proportions and complexion markedly while adding makeup; `027775` changes a pink hat to orange across variants; `055840/makeup_03` has a recognizable red lip but changes brows, eye appearance, and skin texture. Some samples appear to have altered face shape or apparent age. Portraits whose subjects may not be adults need screening and should not be used as adult training sources without verification. These observations are not a measured failure rate for all 18,370 identities, but they rule out automatic acceptance of the existing pairs.

### Ten-style mapping from 60 inspected pairs

`DIRECT` requires a clearly identifiable class **and** a usable, reviewed same-identity pair. `PARTIAL` means a visual ingredient or look is present but class boundaries or pair preservation are insufficient. `NONE` means the sample did not establish a defensible pair for that class, not that the entire archive lacks one. No suffix maps globally to any class.

| Project style | Sample support | Actual evidence |
| --- | --- | --- |
| Natural Makeup | PARTIAL | `062589/makeup_01` and `027775/makeup_03` are restrained, but the intended makeup difference and altered skin/lighting are hard to separate. |
| No-Makeup Makeup | NONE | Near-bare variants are not reliably distinguishable from minimal change or retouching. |
| Soft Glam | PARTIAL | `055840/makeup_01` and `008845/makeup_04` show polished eyes/lips, but individual pair drift and class overlap remain. |
| Smoky Glam | PARTIAL | `055840/makeup_02` shows dark blended eye emphasis; it is bluish and the face is also reconstructed. |
| Dewy Peach | PARTIAL | `003760/makeup_02` suggests warm peach blush, but luminous finish and identity preservation are not established. |
| Rosy Pink | PARTIAL | `048564/makeup_01` and `062589/makeup_02` show rosy components, not uniformly coordinated eyes, cheeks, and lips. |
| Bronze / Golden Glam | NONE | No sampled pair clearly establishes a coordinated bronze/gold look. |
| Matte Nude | NONE | Matte finish versus smoothing or lighting cannot be reliably separated in the sample. |
| Classic Red Lip | PARTIAL | `055840/makeup_03` visibly has a crisp red lip, but eye/brow/skin reconstruction prevents calling the pair training-ready. |
| Bold Evening Glam | PARTIAL | Several strong eye and lip looks exist, including `008845/makeup_01`, but there is no fixed class and drift is common. |

The ten-style taxonomy remains unchanged pending a focused pilot. These 60 inspected pairs do not justify a merge or removal. Nor do they justify calling any existing suffix a class. Colorful teal and purple eye looks occur outside some of our proposed styles; they should be recorded as unmatched rather than forced into a label.

### DATA-M001 role and recommendation

`ROLE A` (direct labelled training pairs) is **not supported**. `ROLE B` (small manually curated subset) is **possible but not yet accepted**; every candidate target would need style and preservation review. `ROLE C` (bare/source identities) is the most immediately useful role, provided adults with suitably bare faces and source-level credit/license records are selected. `ROLE D` applies to style reference and failure analysis, not automatic validation ground truth. `ROLE E` is not warranted for the whole archive because its source portraits and some looks remain useful.

The fastest defensible provisional strategy is **C: selected FFHQ bare portraits plus controlled ten-style targets**, with existing variants considered only as opportunistic `ROLE B` additions when a specific pair passes review. This changes the Stage 1 hybrid-first recommendation because the actual sample shows unstable style positions and repeated face reconstruction. Do **not** generate all targets now. First select two rights-traceable adult source identities and run the separately approved 2 by 10 FLUX Base target pilot. If that pilot repeats severe drift, stop and solve preservation before building the full dataset. The working floor remains 10 train plus 4 held-out identities and 140 accepted pairs for ten styles. All-synthetic would require up to 140 generations; every accepted existing pair reduces that count by one. The exact accepted existing count is currently **zero**, since none has passed the required individual review. Thus 140 is a ceiling, not a commitment. The first GPU stage remains capped at 20 images and is outside this CPU audit.

Remaining unknowns: per-photo FFHQ author/license linkage for selected IDs; makeup-reference derivative rights; whether two selected adult sources can support all ten styles without Base identity drift; the number of existing pairs that survive explicit visual QA; LoRA learning and held-out quality. No Kaggle GPU, training, app wiring, or Hair modification occurred.

## Stage 3: frozen DATA-M001 construction inputs (2026-09-25)

The Supervisor confirmed Strategy C: selected FFHQ-Makeup `bare.jpg` files as sources, with ten explicitly project-labelled targets generated per identity. The existing `makeup_01` through `makeup_05` files are **not classes or training targets**. Stage 1's hybrid recommendation and Stage 2's 10/4 provisional budget are superseded. Pair direction is only bare to makeup; there are no reverse pairs. No GPU generation has occurred in this stage.

The original [NVIDIA FFHQ metadata](https://github.com/NVlabs/ffhq-dataset) was downloaded and verified at 267,793,842 bytes with published MD5 `425ae20f06a4da1d4dc0f46d40ba5fd6`. Its numeric image IDs were joined to the same six-digit archive IDs. The source manifest records each original Flickr photo URL, author, license name and license URL. The FFHQ-Makeup archive retains its verified SHA256 `c15fd40199b4d46050dc864eaed647b0ad41921507c2f99cb1cfec2b46922c6a` and pinned revision `25955d8cb70e97b00f3ee9eacffabc9d3fda81a7`. Dataset-level CC BY-NC-SA 4.0 and per-photo attribution/noncommercial terms must be retained. Source selection is visual, not based on inferred demographic labels. Apparent adulthood and suitability were screened visually, but age, individual consent and any original image-specific rights beyond the recorded metadata are not independently verified. Do not redistribute the source bundle publicly without a rights review.

The immutable split is:

| Split | Identity IDs |
| --- | --- |
| TRAIN, first pilot | `003025`, `054109` |
| TRAIN, remaining | `010126`, `026805`, `031569`, `032501`, `039914`, `051141`, `056266`, `059106` |
| VALIDATION, held out | `057326`, `063802` |

These are twelve visually varied, mostly frontal faces with reasonably clear makeup regions. Some source portraits may already show subtle cosmetics; `003025` in particular has visible lip color, so Natural versus No-Makeup may be difficult to judge. The first 20-output tranche must test whether this is a material problem. The two validation identities never enter pilot or training generation. Exact source hashes, members, source credits, and licenses are in the [source manifest](../../.tmp/data_m001/selected_v2/source_manifest.json); the [selection sheet](../../.tmp/data_m001/selected_v2/source_selection_sheet.jpg) shows all twelve. These `.tmp` artifacts are local and excluded from Git.

The ten candidate style IDs and current generation prompts are in [config.json](../../data/makeup/DATA-M001/config.json). The exact prompt for each generation is `instruction` plus one space plus `preservation_instruction`, with no identity-specific additions. The style IDs are `natural_makeup`, `no_makeup_makeup`, `soft_glam`, `smoky_glam`, `dewy_peach`, `rosy_pink`, `bronze_golden_glam`, `matte_nude`, `classic_red_lip`, and `bold_evening_glam`. The **first 20** used the original config stored immutably in their downloaded results ZIP; the local No-Makeup instruction was subsequently revised for a future bounded rerun and must not be attributed to those existing images. The two deliberately close pairs, Natural versus No-Makeup and Smoky versus Bold Evening, need explicit separation review, not an automatic merge.

The [preparer](../../scripts/data_m001_prepare.py) verifies both upstream digests, checks 10/2 split integrity and per-photo credits/licenses, extracts only twelve bare JPEGs, writes source hashes and a selection sheet, and creates `F:/HAIR/.tmp/data_m001/data_m001_kaggle_input.zip` (SHA256 `dd01790aac7828b1b67a0abe382129b832d7d59376db219aecc665b1b87b187c`). The bundle includes `config.json`, `source_manifest.json`, `source_selection_sheet.jpg`, `sources/<id>.jpg`, and `data_m001_generate_kaggle.py`. No existing makeup variants are included. The [Kaggle runner](../../notebooks/data_m001_generate_kaggle.py) has a CPU plan mode and GPU pilot, retry, and remaining modes. The [finalizer](../../scripts/data_m001_finalize.py) requires 120 explicit human ACCEPT decisions, valid source/target hashes, exact prompts, no adapter, ten style IDs, 100 TRAIN pairs and 20 VALIDATION pairs. It writes captioned directional pair folders, a final manifest and QA report. Nothing in this path imports Hair code.

### Kaggle execution and artifact contract

Use a Kaggle T4 GPU notebook with Internet on. Upload the prepared small input ZIP as a private Kaggle Dataset. This notebook cell locates the exact ZIP under Kaggle Input, avoiding any assumption about Kaggle's dataset folder name, then extracts it into `/kaggle/working/data_m001_input`:

```python
from pathlib import Path
from zipfile import ZipFile

matches = list(Path('/kaggle/input').rglob('data_m001_kaggle_input.zip'))
assert len(matches) == 1, f'Expected exactly one DATA-M001 input ZIP: {matches}'
input_dir = Path('/kaggle/working/data_m001_input')
input_dir.mkdir(parents=True, exist_ok=True)
with ZipFile(matches[0]) as source:
    assert source.testzip() is None
    source.extractall(input_dir)
print(input_dir)
```

If Kaggle presents the ZIP contents as an already extracted dataset directory, point `--inputs` at the folder containing `config.json` and `source_manifest.json` instead. The runner's CPU plan can be checked before enabling GPU:

```text
python /kaggle/working/data_m001_input/data_m001_generate_kaggle.py --phase plan --inputs /kaggle/working/data_m001_input
```

With GPU available, run exactly the first tranche and stop for human review:

```text
python /kaggle/working/data_m001_input/data_m001_generate_kaggle.py --phase pilot --inputs /kaggle/working/data_m001_input --output /kaggle/working/data_m001
```

This runs pinned `black-forest-labs/FLUX.2-klein-base-4B` revision `a3b4f4849157f664bdbc776fd7453c2783562f4d`, FP16 with CPU offload, 512 by 512, 20 steps, guidance 4.0 and seed 1977, **no LoRA**. The first two train IDs each receive all ten styles, for 20 attempts. Based only on the Base pilot's roughly 73 seconds per image, 20 generations imply about 25 minutes of generation plus model load, downloads, setup and any retry. This is an estimate, not a measured DATA-M001 runtime. The remaining 100 would take about 2 hours at the same per-image rate, again excluding overhead and retries.

Download `/kaggle/working/data_m001_results.zip` before ending the session. It contains the twelve originals, pinned config and source manifest, full resolution targets, per-attempt JSON, `reviews.json` template, failure records if any, generation log, per-identity contact sheets, runtime data and plan. Failed generations are recorded rather than discarded. Each review cell requires `ACCEPT`, `RETRY`, or `REJECT` with reviewer, note, and optional failure tags. Only a human may set ACCEPT. A `RETRY` may trigger one bounded second attempt with seed 1978; no third attempt is supported. If a style fails on both pilot identities, revise that one style instruction and rerun both identities as a new documented prompt version **before** full generation. The current runner intentionally does not auto-tune prompts or auto-run the remaining 100.

After all 20 pilot cells receive an explicit ACCEPT, restore the downloaded pilot results ZIP into `/kaggle/working/data_m001` if using a fresh Kaggle session. Then `--phase remaining --pilot-reviews /kaggle/working/data_m001/reviews.json` can run the other ten identities and ten styles. The runner checks the twenty accepted image hashes and records before loading a GPU model. This gate should be used only after Project Lead review. The finalizer later requires exactly 100 TRAIN and 20 VALIDATION accepted pairs and produces `pairs/train/...`, `pairs/validation/...`, `final_manifest.json`, and `qa_report.json`. Rejected or replaced sources/targets require documented versioning rather than silent changes to the frozen manifest.

### Current execution boundary

The local CPU plan and nine targeted audit/pipeline tests passed. At preparation time, the Kaggle browser was inaccessible from this task and no Kaggle CLI credentials were configured here. The user subsequently ran the notebook and supplied the results, as recorded in the Stage 4 update. The remaining 100, final DATA-M001, and MAKEUP-001 training are not authorized by evidence at this point.

### Stage 4 update: first 20 targets generated and inspected

The Supervisor ran the pilot on Kaggle Tesla T4 and downloaded its results ZIP. The [pilot review](../experiments/DATA-M001-pilot-review.md) supersedes the preceding execution-boundary paragraph. The ZIP and all 20 sidecars passed technical audit: 20 attempted, 20 successful, zero failed, exact prompts and pinned settings, no LoRA, source/target hashes and image decoding verified. Full-resolution review found recurring facial reconstruction, extreme smoothing, mask-like cosmetics, and weak No-Makeup separation. **No result has a human ACCEPT review yet.** Do not run the remaining 100 or finalize DATA-M001 until the visual blocker is addressed and the Supervisor reviews the corrective plan.

### Stage 5 update: CPU identity preservation

The [preservation review](../experiments/DATA-M001-preservation-review.md) documents a separate Makeup-only CPU appearance-transfer script, all 20 preserved candidates, four Original / Raw / Preserved comparison sheets, masks, hashes and per-image observations. Source-defined protected pixels are exactly unchanged across all 20, and identity/geometry/background preservation improved visibly. Subtle style separation remains weak and high-contrast lips can look too uniform. No target is marked ACCEPT or finalized. The current finalizer still expects raw pilot targets; it must be changed to consume provenance-checked preserved targets **only after** the preservation visual gate passes. Do not run the other 100 until then.

### Stage 6 update: focused Preservation V3

The [V3 review](../experiments/DATA-M001-preservation-v3-review.md) compares Original, Raw, V2 and V3 for all 20 existing samples. The CPU V3 compositor narrowed eye/cheek fields, transferred complexion and local cosmetic Lab statistics with bounded style strengths, and feathered source lip tissue while keeping inner mouth and all other protected labels exact. Technical checks passed all 20, but visual review classified six plausible candidates, three raw outputs needing replacement, and eleven systematic preservation failures. V3 is **not frozen**, the official review states remain pending, and the remaining 100 and training stay stopped. The next correction is localized appearance transfer without median-color collapse, not another dataset or model decision.

### Stage 7 update: localized Preservation V4

The [V4 review](../experiments/DATA-M001-preservation-v4-review.md) compares Original, Raw, V2, V3 and V4 for the same 20 images. The CPU V4 compositor transfers bounded spatial LAB differences in source-anchored skin, eye, cheek, lip and brow regions. Original geometry and parser-defined protected pixels remain exact in all 20. Full-resolution visual review found only three plausible V4 candidates, three raw outputs requiring future replacement, and fourteen preservation failures. V4 does **not** meet the 16 to 18 usable-target gate and is **not frozen**. The demonstrated blocker is raw facial reconstruction contaminating the spatial cosmetic difference map. No official training-pair ACCEPT decisions exist; the remaining 100 and MAKEUP-001 training remain stopped.

### Stage 8 update: final target method and bounded global V2 prompt pass

The Project Lead selected original global FLUX Base editing as the final DATA-M001 target method. The prior preservation, compositing and inpainting work remains research evidence, but its outputs will not be DATA-M001 targets. The first global 20 are diagnostic only. A single bounded revision of the ten style prompts and shared photo-preservation instruction is packaged for the same two TRAIN identities, without changing model revision, inference steps, guidance, seed, size, precision or no-LoRA condition. The [global V2 handoff](../experiments/DATA-M001-global-v2.md) records the exact bundle and next 20-image Kaggle run. The remaining 100 and MAKEUP-001 training follow only after the new 20 have been generated and reviewed under the Project Lead's updated ACCEPT, RETRY_ONCE and REJECT criteria.

### Stage 9 update: bounded global V2 result and stop gate

The Project Lead ran the one approved prompt-only rerun. The downloaded ZIP passed CRC and technical audit: 20 attempts, 20 successful Base-only images, zero recorded generation failures, pinned revision and matching hashes. The [Original/V1/V2 visual review](../experiments/DATA-M001-global-v2-review.md) found no credible ten-style training set: both identities still show facial reconstruction or smoothing, oversized cosmetic regions, and hard mouth/lip boundaries. The Project Lead judged the outputs visually unacceptable. This is a dataset-target quality failure, not an inference runtime failure. All `reviews.json` entries remain `PENDING`, so the accepted DATA-M001 count is still **zero**. The revised prompts and settings are **not frozen** for full generation. Do not run the remaining 100, finalize DATA-M001, train MAKEUP-001 or connect live Makeup inference without an explicit decision resolving this concrete blocker. The earlier Stage 8 paragraph is the historical preparation state, superseded by this result.

### Stage 10 update: real paired DATA-M001 finalized

The Supervisor's 2026-09-26 decision superseded the artificial ten-style target plan. MAKEUP-001 is now a general bare-to-makeup edit LoRA; ten product styles remain inference prompt presets, not training classes. The earlier global, preservation and inpainting outputs remain research evidence only and **none appears in this dataset**. The verified real FFHQ-Makeup archive is the sole image source. Its suffix positions are stored as provenance, never relabeled as global styles.

The selected TRAIN identities are `003681`, `006553`, `015406`, `017290`, `020867`, `022625`, `035149`, `036948`, `051141`, `059106`. The held-out VALIDATION identities are `054109`, `056266`. All five existing bare-to-makeup target pairs per identity were retained, so there are exactly 50 TRAIN and 10 VALIDATION directional pairs. There are zero rejected pairs within this final selection. The previously selected `003025` was not carried forward because its archive targets changed facial appearance strongly; other screened but unselected identities included examples with exaggerated eye pigment (`027921`, `049206`), hair change (`041984`), and stronger reconstruction or weak cosmetics. Selection used contact sheets of the old twelve and 29 targeted alternatives, not exhaustive review of 18,370 identities. These exclusions are identity selection decisions, not hidden pair deletion from the final manifest.

The Project Lead approved all 60 pairs after viewing the three private contact sheets on 2026-09-26. This is a practical visual gate: same recognizable person and visible cosmetic change, not pixel-exact preservation. Some approved pairs still smooth or retouch skin, and the small dataset may teach unwanted reconstruction. The held-out Base versus MAKEUP-001 evaluation must judge that risk. Age, subject consent and current downstream rights are not independently verified; noncommercial academic use, CC BY-NC-SA 4.0 and the original FFHQ photo attribution/license records must be respected.

The [frozen paired selection](../../data/makeup/DATA-M001-paired/selection.json), [pair finalizer](../../scripts/data_m001_paired.py), and private final directory `F:/HAIR/.tmp/data_m001/paired_selection/final_v1/` preserve archive members, source and target hashes, per-photo author/URL/license, split, explicit human review, caption, and QA. `train/reference/` and `train/target/` have matching stems and captions; validation has the same structure. Captions use a general visible-makeup editing instruction, because the archive positions do not provide trustworthy semantic labels and automated per-image descriptions were not verified. The private review sheets are in `F:/HAIR/.tmp/data_m001/paired_selection/prepared_v1/contact_sheets/`. Final QA reports 12 distinct identities, 60 unique target hashes, 50/10 pairs, zero split leakage and 60 Project Lead ACCEPT reviews.

The [MAKEUP-001 handoff](../experiments/MAKEUP-001-plan.md) packages only these reviewed real pairs, an isolated T4 training runner and the ten inference presets. CPU dataset preparation and training config checks passed, but **no Kaggle training or model evaluation has run**. The earlier Stage 9 stop applied to the failed synthetic path and is superseded by this reviewed real-pair direction.
