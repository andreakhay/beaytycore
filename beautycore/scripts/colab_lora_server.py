# ============================================================================
#  BeautyCore — LoRA inference server for Google Colab  (Stable Diffusion 1.5)
# ============================================================================
#  Serves the trained BeautyCore LoRA over HTTP so the Next.js app can call it.
#
#  This is built for the LoRA in BeautyCore_Model/, whose training config was:
#
#      pretrained_model_name_or_path : runwayml/stable-diffusion-v1-5
#      resolution                    : 512
#      rank                          : 32
#      max_train_steps               : 1500   (checkpoints at 500/1000/1500)
#      validation_prompt             : null   <-- never validated during training
#
#  SD 1.5, NOT SDXL. Serving it on an SDXL base fails outright: this LoRA's
#  cross-attention layers are 768-dim, SDXL's are 2048.
#
#  NAIL MASKING
#  ------------
#  Previews run as masked inpainting rather than plain img2img. A fingernail is
#  roughly 1% of a hand photo, and img2img spreads its changes evenly over the
#  whole frame — so in practice it restyles the rings and the background and
#  leaves the nails alone. The app sends one bounding box per nail (from Gemini,
#  see lib/ai/detect.ts); this server rasterises them into a mask and repaints
#  only inside it. That is what lets strength go high enough to genuinely change
#  nail colour without touching anything else.
#
#  Requests without mask_boxes still work — they take the old img2img path.
#
#  HOW TO USE
#  ----------
#  1. Runtime > Change runtime type > T4 GPU. Then run the cells in order.
#  2. Upload pytorch_lora_weights.safetensors, or mount Drive and point
#     LORA_PATH at BeautyCore_Model/.
#  3. Run Cell 3 (smoke test) and LOOK AT THE OUTPUT before wiring up the app.
#     Nothing was validated during training, so this is the first time anyone
#     sees what this model actually produces. To exercise the masked path here
#     too, paste real boxes into NAIL_BOXES — the cell explains where from.
#  4. Copy the printed https://....trycloudflare.com URL into .env.local:
#         PREVIEW_PROVIDER=lora
#         LORA_ENDPOINT_URL=https://....trycloudflare.com
#     Restart `npm run dev`.
#
#  IMPORTANT
#  ---------
#  * The URL changes every time this notebook restarts. Re-paste it each session.
#  * Keep this tab open and the runtime alive during your demo.
#  * Free-tier Colab reclaims idle GPUs — interact with the page occasionally.
# ============================================================================


# --- Cell 1: install -------------------------------------------------------
# Colab's base image ships torchao 0.10.0. Current peft/diffusers probe for
# torchao and *raise* if the installed version is too old, rather than skipping
# it — which kills load_lora_weights() with a confusing ImportError. Nothing
# here needs torchao (it is a quantisation library), so remove it outright.
# Upgrading it instead would drag in a different torch and break CUDA.
!pip uninstall -y -q torchao

!pip install -q "diffusers>=0.31" transformers accelerate peft safetensors \
                fastapi "uvicorn[standard]" nest-asyncio pillow
!wget -q -O cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
!chmod +x cloudflared


# --- Cell 2: load the pipeline ---------------------------------------------
import os, io, re, time, base64, threading, subprocess
import torch
from PIL import Image, ImageDraw, ImageFilter
from diffusers import (
    StableDiffusionImg2ImgPipeline,
    StableDiffusionInpaintPipeline,
    StableDiffusionPipeline,
)

# Point this at the .safetensors file, or at a directory containing one.
# To compare training stages, swap in ".../BeautyCore_Model/checkpoint-1000".
# The top-level file is the finished 1500-step export; the checkpoint folders
# hold the same weights in PEFT key naming, which _load_lora_state converts.
LORA_PATH = "/content/pytorch_lora_weights.safetensors"

# How strongly the LoRA is applied. 0 = base model, 1 = full strength.
DEFAULT_LORA_SCALE = 0.8

# img2img input size. SD 1.5 trains at 512; pushing far past that invites
# duplicated fingers and doubled subjects. 640 keeps a little more nail
# detail while staying close to native. Lower it to 512 if you see artefacts.
MAX_SIDE = 640

# Mask geometry, used when the app sends nail boxes (see build_mask).
#   MASK_PAD  grows each box outward before the ellipse is drawn.
#   MASK_BLUR feathers the boundary so the new nail fades into the finger
#             instead of reading as a pasted cut-out.
#
# These two are NOT independent, which makes tuning either one alone a trap.
# Blur spreads the edge outward AND erodes the fully-white core inward, so a
# large blur both spills paint onto skin and weakens the repaint where you
# actually want it. Padding then hides the weak core by enlarging the shape,
# which spills further still. Measured on a real 435x520 hand photo, five nails
# whose bare ellipses are 4.61% of the frame:
#
#   pad / blur   touched   full-strength core (share of nail)
#   0.15 / 5      14.5%    2.70%  (59%)   <- the original guess
#   0.05 / 5      11.6%    1.43%  (31%)   cutting pad alone starves the core
#   0.05 / 2       7.7%    3.56%  (77%)   <- current: better on both axes
#
# At 0.15/5 the mask reached well past each nail onto the fingertip, and the
# model filled that space with more nail: previews came back with noticeably
# longer, more almond nails than the client actually had, overriding a prompt
# that asked for short ones. Halving pad and blur fixed the drift and made the
# colour change stronger, because more of each nail is repainted at full weight.
#
# Note blur is in absolute pixels and does not scale with MAX_SIDE, so it hits
# a small image proportionally harder. Re-measure if MAX_SIDE changes.
# Tune by looking at the smoke-test overlay, not by guessing.
MASK_PAD = 0.05
MASK_BLUR = 2

# runwayml deleted their Stable Diffusion repos from HuggingFace in 2024, so the
# id recorded in hparams.yml now 404s. These are the surviving mirrors of the
# same base weights; the first one that loads wins.
BASE_CANDIDATES = [
    "stable-diffusion-v1-5/stable-diffusion-v1-5",
    "sd-legacy/stable-diffusion-v1-5",
    "runwayml/stable-diffusion-v1-5",
]

img2img = None
BASE_MODEL = None
for candidate in BASE_CANDIDATES:
    # These mirrors publish F32 weights with no fp16 variant, so do NOT pass
    # variant="fp16" — it raises. torch_dtype casts at load time instead.
    # Try safetensors first, then fall back for any mirror that only has .bin.
    for use_st in (True, False):
        try:
            print(f"Trying base model: {candidate} (safetensors={use_st}) ...")
            img2img = StableDiffusionImg2ImgPipeline.from_pretrained(
                candidate,
                torch_dtype=torch.float16,
                use_safetensors=use_st,
                # SD 1.5 ships an NSFW checker that false-positives on close-up
                # skin — hands and faces, i.e. exactly this app's input — and
                # returns a solid black image. Off, or previews mysteriously blank.
                safety_checker=None,
                requires_safety_checker=False,
            ).to("cuda")
            BASE_MODEL = candidate
            print(f"✓ Loaded {candidate}")
            break
        except Exception as e:
            print(f"  ✗ {type(e).__name__}: {str(e)[:160]}")
    if img2img is not None:
        break

if img2img is None:
    raise RuntimeError(
        "Could not load any SD 1.5 base model. Check your internet connection, "
        "or pass a local path / another mirror in BASE_CANDIDATES."
    )

# Text-to-image reuses the same weights, so this costs no extra VRAM. It is
# what the smoke test uses to show what the LoRA learned in isolation.
txt2img = StableDiffusionPipeline(**img2img.components)
txt2img.set_progress_bar_config(disable=True)
img2img.set_progress_bar_config(disable=True)

# Masked inpainting — the path that makes nail previews actually work.
#
# Also the same UNet, so also free in VRAM, and the LoRA loaded below still
# applies: a LoRA modifies the attention layers (to_q/to_k/to_v/to_out), which
# are shared, and nothing about the pipeline wrapper changes them.
#
# Note this is the standard SD 1.5 checkpoint, not the dedicated 9-channel
# inpainting one. diffusers handles that case explicitly: when
# unet.config.in_channels == 4 it blends latents inside the mask rather than
# feeding extra mask channels to the UNet. That is what we want — the dedicated
# inpainting checkpoint would be another 4 GB download AND a base this LoRA was
# never trained against.
inpaint = None
try:
    inpaint = StableDiffusionInpaintPipeline.from_pipe(img2img)
except Exception as e:
    print(f"  from_pipe unavailable ({type(e).__name__}), trying components...")
    try:
        inpaint = StableDiffusionInpaintPipeline(
            **img2img.components, requires_safety_checker=False
        )
    except Exception as e2:
        print("=" * 70)
        print(f"⚠ INPAINTING UNAVAILABLE: {type(e2).__name__}: {e2}")
        print("  Nail masking will silently fall back to plain img2img, which")
        print("  restyles rings and background more than nails. Try:")
        print("      !pip install -U diffusers")
        print("=" * 70)

if inpaint is not None:
    inpaint.set_progress_bar_config(disable=True)
    print("✓ Inpainting pipeline ready (nail masking available)")


def _safe_move(src: str, dst: str) -> str:
    """shutil.move raises if src and dst are the same file; uploads often are."""
    import shutil

    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.move(src, dst)
    return dst


def _resolve_lora(path: str) -> str | None:
    """
    Find the LoRA, trying increasingly desperate measures:

      1. the exact path
      2. a .safetensors inside it, if `path` is a directory
      3. anywhere under /content — drag-and-drop uploads land in a subfolder
         more often than you would think, and Drive mounts sit levels down
      4. ask for it with a file picker

    Only returns None if all four fail. Step 4 matters: the file pane silently
    drops uploads if the runtime reconnects mid-transfer, and the picker is the
    reliable path.
    """
    import glob

    if os.path.isfile(path):
        return path

    if os.path.isdir(path):
        cand = os.path.join(path, "pytorch_lora_weights.safetensors")
        if os.path.isfile(cand):
            return cand
        for f in sorted(os.listdir(path)):
            if f.endswith(".safetensors"):
                return os.path.join(path, f)

    hits = sorted(glob.glob("/content/**/*.safetensors", recursive=True))
    if hits:
        print(f"⚠ Nothing at {path}, but found {hits[0]} — using that.")
        return hits[0]

    try:
        from google.colab import files
    except Exception:
        return None

    print("─" * 70)
    print("No .safetensors found anywhere under /content.")
    print("Select pytorch_lora_weights.safetensors (25 MB) from your")
    print("BeautyCore_Model folder. You can select a nail photo at the same")
    print("time to enable the image-to-image preview further down.")
    print("─" * 70)
    try:
        uploaded = files.upload()
    except Exception as e:
        print(f"Upload picker unavailable: {type(e).__name__}: {e}")
        return None

    found = None
    for fn in list(uploaded):
        if fn.endswith(".safetensors"):
            found = _safe_move(fn, "/content/pytorch_lora_weights.safetensors")
        elif fn.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            _safe_move(fn, "/content/test.jpg")
            print("✓ Saved your photo as /content/test.jpg")
    return found


def _find_test_photo() -> str | None:
    """Any photo in /content, so the filename does not have to be exactly right."""
    import glob

    for exact in ("/content/test.jpg", "/content/test.jpeg", "/content/test.png"):
        if os.path.isfile(exact):
            return exact
    for p in sorted(glob.glob("/content/*")):
        if os.path.isfile(p) and p.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            return p
    return None


LORA_FILE = _resolve_lora(LORA_PATH)
LORA_READY = False


def _load_lora_state(path: str):
    """
    Read a LoRA into a state dict, normalising the key naming first.

    The two files in the model folder are NOT interchangeable:

      pytorch_lora_weights.safetensors  (top level)  -> diffusers naming,
                                                        `lora.down` / `lora.up`
      checkpoint-*/pytorch_lora_weights.safetensors  -> PEFT naming,
                                                        `lora_A` / `lora_B`

    The final export was converted on the way out; the intermediate checkpoints
    were not. load_lora_weights() wants the diffusers spelling, so translate
    when we see the PEFT one — otherwise swapping in a checkpoint to compare
    training stages dies on unexpected keys.
    """
    from safetensors.torch import load_file

    state = load_file(path)
    if any(".lora_A" in k or ".lora_B" in k for k in state):
        state = {
            k.replace(".lora_A.", ".lora.down.").replace(".lora_B.", ".lora.up."): v
            for k, v in state.items()
        }
        print("  (converted PEFT lora_A/lora_B keys to diffusers naming)")
    return state


if LORA_FILE:
    size = os.path.getsize(LORA_FILE)
    try:
        img2img.load_lora_weights(_load_lora_state(LORA_FILE))
        LORA_READY = True
        print(f"✓ LoRA loaded from {LORA_FILE} ({size:,} bytes)")
    except Exception as e:
        print("=" * 70)
        print(f"✗ LoRA FAILED TO LOAD: {type(e).__name__}: {e}")
        if "torchao" in str(e):
            print("")
            print("  This is Colab's environment, not your model. The base image")
            print("  ships an old torchao and peft raises instead of skipping it.")
            print("  Fix: run  !pip uninstall -y torchao  then Runtime >")
            print("  Restart session, then re-run cells 1 and 2. The base model")
            print("  stays cached on disk, so the reload takes seconds.")
        else:
            print("  If this was a key-name error: pip install -U diffusers peft")
        print("=" * 70)
else:
    print("=" * 70)
    print("⚠ NO LoRA FILE FOUND — this notebook is serving the BASE model only.")
    print(f"  Looked at: {LORA_PATH}, then everywhere under /content.")
    print("  Previews would be generic Stable Diffusion, not your trained style.")
    print("  Upload pytorch_lora_weights.safetensors, then RE-RUN THIS CELL.")
    print("=" * 70)


def set_lora_scale(scale: float):
    """
    Apply a LoRA weight. diffusers changed this API across versions, so try the
    modern PEFT path first and report whether the caller must fall back to
    passing cross_attention_kwargs at call time.
    """
    if not LORA_READY:
        return None
    try:
        names = img2img.get_active_adapters()
        if names:
            img2img.set_adapters(names, adapter_weights=[scale] * len(names))
            return "adapters"
    except Exception:
        pass
    return "cross_attention_kwargs"


SCALE_MODE = set_lora_scale(DEFAULT_LORA_SCALE)
print(f"LoRA scale mechanism: {SCALE_MODE or 'n/a (no LoRA)'}")


def _call_kwargs(scale: float) -> dict:
    """Per-request kwargs needed to honour `scale` on this diffusers version."""
    if not LORA_READY:
        return {}
    if SCALE_MODE == "adapters":
        set_lora_scale(scale)
        return {}
    return {"cross_attention_kwargs": {"scale": scale}}


NEGATIVE = (
    "ugly, disfigured, deformed, blurry, low quality, watermark, text, "
    "extra fingers, missing fingers, fused fingers, mutated hands, bad anatomy"
)


def _decode(b64: str) -> Image.Image:
    """Base64 (with or without data: prefix) -> RGB image sized for SD 1.5."""
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

    w, h = img.size
    scale = min(MAX_SIDE / max(w, h), 1.0)
    w, h = max(int(w * scale) // 8 * 8, 384), max(int(h * scale) // 8 * 8, 384)
    return img.resize((w, h), Image.LANCZOS)


def build_mask(size, boxes, pad=None, blur=None):
    """
    Rasterise nail bounding boxes into an inpainting mask. White = repaint.

    `boxes` are [ymin, xmin, ymax, xmax] scaled 0-1000 — Gemini's native output
    format, produced by lib/ai/detect.ts in the app and by
    scripts/nail-boxes.ts on the command line.

    Ellipses rather than rectangles, because a nail is rounded and a rectangle
    puts paint on the skin at all four corners. Blurred at the end so the new
    nail fades into the finger; a hard edge reads as a pasted cut-out.
    """
    pad = MASK_PAD if pad is None else pad
    blur = MASK_BLUR if blur is None else blur

    W, H = size
    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)

    for box in boxes:
        ymin, xmin, ymax, xmax = (float(v) for v in box[:4])
        x0, y0 = xmin / 1000 * W, ymin / 1000 * H
        x1, y1 = xmax / 1000 * W, ymax / 1000 * H
        dx, dy = (x1 - x0) * pad, (y1 - y0) * pad
        draw.ellipse([x0 - dx, y0 - dy, x1 + dx, y1 + dy], fill=255)

    return mask.filter(ImageFilter.GaussianBlur(blur))


# One GPU, and `from_pipe` deliberately shares components between txt2img,
# img2img and inpaint — that sharing is exactly what makes the inpaint pipeline
# cost no extra VRAM. It also means all three share ONE PNDMScheduler, and that
# scheduler is stateful: it accumulates `ets` across denoising steps. Two
# overlapping renders corrupt each other's state and die with
#
#     IndexError: list index out of range    (scheduling_pndm.py, step_plms)
#
# This is not an exotic race. uvicorn serves requests concurrently, and the
# advisor renders three recommendations each with its own Generate button, so a
# client clicking two of them is enough. Running a notebook cell while an API
# request is in flight does it too — which is how it was found.
#
# Serialising costs nothing real: one GPU cannot render two images faster than
# it renders them back to back, and two concurrent SD 1.5 renders risk OOM on
# the T4 that free Colab hands out.
_RENDER_LOCK = threading.Lock()


def _render(prompt, image=None, strength=0.5, scale=DEFAULT_LORA_SCALE,
            steps=40, guidance=7.5, seed=None, mask_boxes=None,
            mask_strength=0.95):
    """
    Single entry point used by both the smoke test and the API. Three paths:

      image + mask_boxes  masked inpainting. Only the nails are repainted, so
                          `mask_strength` can be high enough to actually change
                          their colour without touching rings or background.
                          This is the one that works.

      image only          img2img across the whole frame at `strength`. Noise
                          is spread uniformly, and a nail is ~1% of the frame,
                          so the model reliably restyles the jewellery and
                          leaves the nails alone. Kept as the fallback for when
                          nail detection returns nothing.

      neither             txt2img — what the smoke test uses to see the LoRA in
                          isolation.
    """
    gen = torch.Generator("cuda").manual_seed(seed) if seed is not None else None
    opts = dict(
        prompt=prompt,
        negative_prompt=NEGATIVE,
        guidance_scale=guidance,
        generator=gen,
        **_call_kwargs(scale),
    )

    if image is not None and mask_boxes and inpaint is not None:
        # height/width are NOT optional here, unlike every other pipeline call.
        # img2img derives the output size from the input image; the inpaint
        # pipeline instead falls back to the UNet's own 512x512 and stretches
        # the photo AND the mask to square. The mask still lands on the nails
        # (both are stretched identically) so the result looks right at a
        # glance, but a 528x640 portrait hand came back ~20% too wide.
        # _decode already snapped both sides to a multiple of 8, so these can
        # be passed straight through.
        W, H = image.size
        return inpaint(
            image=image,
            mask_image=build_mask(image.size, mask_boxes),
            width=W,
            height=H,
            # Unlike img2img, this is bounded by the mask, so it can go high.
            strength=max(0.1, min(mask_strength, 1.0)),
            num_inference_steps=steps,
            **opts,
        ).images[0]

    if image is not None:
        # img2img runs steps*strength actual denoising steps, so keep `steps`
        # generous or low-strength renders come out under-cooked.
        return img2img(
            image=image,
            strength=max(0.1, min(strength, 0.95)),
            num_inference_steps=steps,
            **opts,
        ).images[0]

    return txt2img(width=512, height=512, num_inference_steps=steps, **opts).images[0]


def render(*args, **kwargs):
    """Serialised entry point. See _RENDER_LOCK for why the lock is required."""
    with _RENDER_LOCK:
        return _render(*args, **kwargs)


print("✓ Pipeline ready")


# --- Cell 3: SMOKE TEST — run this and actually look at it -----------------
#  Training used validation_prompt: null, so no sample was ever generated
#  during those 1500 steps. Two things can go wrong silently:
#    1. the LoRA loads but is never applied (output == base model)
#    2. the LoRA trained on captions nobody wrote down, so plain prompts
#       don't activate the style
#  This cell catches both. Compare the columns: if they look identical, the
#  LoRA is not reaching the UNet and previews will be indistinguishable from
#  stock SD 1.5.

from IPython.display import display

TEST_PROMPT = "close-up photo of manicured fingernails, glossy almond nails, salon quality"
SEED = 42


def grid(images, labels, cell=320):
    cols = len(images)
    canvas = Image.new("RGB", (cell * cols, cell + 28), "white")
    for i, im in enumerate(images):
        canvas.paste(im.resize((cell, cell), Image.LANCZOS), (i * cell, 28))
    try:
        from PIL import ImageDraw
        d = ImageDraw.Draw(canvas)
        for i, lab in enumerate(labels):
            d.text((i * cell + 8, 8), lab, fill="black")
    except Exception:
        print(" | ".join(labels))
    return canvas


if LORA_READY:
    print("Rendering LoRA scale sweep (same seed, so differences are the LoRA)...")
    scales = [0.0, 0.5, 0.8, 1.0]
    imgs = [render(TEST_PROMPT, scale=s, seed=SEED, steps=30) for s in scales]
    display(grid(imgs, [f"scale {s}" for s in scales]))

    # Numeric check — eyeballing can miss a subtle no-op.
    import numpy as np
    base_arr = np.asarray(imgs[0], dtype=np.float32)
    full_arr = np.asarray(imgs[-1], dtype=np.float32)
    delta = float(np.abs(base_arr - full_arr).mean())
    print(f"\nMean pixel difference, scale 0.0 vs 1.0: {delta:.2f}")
    if delta < 1.0:
        print("✗ FAIL — the LoRA is NOT affecting output. Previews would be")
        print("  identical to stock SD 1.5. Check the load step above.")
    else:
        print("✓ PASS — the LoRA measurably changes the output.")
else:
    print("=" * 70)
    print("  SMOKE TEST SKIPPED — NO LoRA IS LOADED. Nothing was tested.")
    print("")
    print("  Scroll up to the previous cell and read its output. It printed")
    print("  either '⚠ NO LoRA FILE FOUND' (the upload did not land) or")
    print("  '✗ LoRA FAILED TO LOAD' (a real error worth reporting).")
    print("")
    print("  Fix that, re-run the previous cell, then re-run this one.")
    print("=" * 70)


# Optional but the more important of the two tests: any photo in /content gets
# previewed through the exact path the app uses.
#
# Paste real boxes here to test masked inpainting, which is what the app does.
# Get them by running this on the same photo, on your own machine:
#
#     npx tsx scripts/nail-boxes.ts path/to/photo.jpg
#
# It prints a ready-to-paste `NAIL_BOXES = [...]` line. Leave this empty and
# you get the old unmasked img2img sweep instead — which is worth seeing once,
# because it shows the problem masking solves: the rings change, the nails
# don't.
NAIL_BOXES = []

TEST_PHOTO = _find_test_photo()


def mask_overlay(src, mask):
    """Wash the masked region in pink so you can see where paint will land."""
    tint = Image.composite(Image.new("RGB", src.size, (255, 0, 140)), src, mask)
    return Image.blend(src, tint, 0.5)


if LORA_READY and TEST_PHOTO:
    print(f"\nUsing your photo: {TEST_PHOTO}")
    src = _decode(base64.b64encode(open(TEST_PHOTO, "rb").read()).decode())

    if NAIL_BOXES and inpaint is not None:
        mask = build_mask(src.size, NAIL_BOXES)
        area = sum(
            (b[2] - b[0]) * (b[3] - b[1]) for b in NAIL_BOXES
        ) / (1000 * 1000) * 100
        print(f"{len(NAIL_BOXES)} nail boxes covering ~{area:.1f}% of the frame.")
        print("CHECK THE SECOND PANEL: the pink must sit on the nail plates.")
        print("If it is on knuckles or the ring, re-run nail-boxes.ts — a wrong")
        print("mask at strength 0.95 will repaint whatever it covers.\n")

        masked = render(
            TEST_PROMPT, image=src, mask_boxes=NAIL_BOXES,
            mask_strength=0.95, seed=SEED,
        )
        # Same strength with no mask, for contrast. This is the comparison that
        # justifies the whole approach.
        unmasked = render(TEST_PROMPT, image=src, strength=0.95, seed=SEED)

        display(grid(
            [src, mask_overlay(src, mask), masked, unmasked],
            ["original", "mask", "masked 0.95", "UNmasked 0.95"],
        ))
    else:
        if NAIL_BOXES:
            print("NAIL_BOXES is set but the inpainting pipeline failed to build.")
            print("Scroll up for the reason. Falling back to the img2img sweep.\n")
        strengths = [0.35, 0.5, 0.65]
        outs = [render(TEST_PROMPT, image=src, strength=s, seed=SEED) for s in strengths]
        print("img2img strength sweep — note how little the nails change:")
        display(grid([src] + outs, ["original"] + [f"strength {s}" for s in strengths]))
elif LORA_READY:
    print("\n(No photo in /content. Upload any nail photo and re-run this cell")
    print(" to preview the image-to-image path the app actually uses.)")


# --- Cell 4: the API -------------------------------------------------------
import nest_asyncio, uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

nest_asyncio.apply()
app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


class GenerateRequest(BaseModel):
    prompt: str
    image: Optional[str] = None       # base64, with or without data: prefix
    prompt_strength: float = 0.5      # img2img: 0 = keep original, 1 = ignore it
    num_inference_steps: int = 40
    guidance_scale: float = 7.5
    lora_scale: float = DEFAULT_LORA_SCALE

    # Nail boxes as [ymin, xmin, ymax, xmax] scaled 0-1000, from Gemini via
    # lib/ai/detect.ts. Present -> masked inpainting; absent -> img2img.
    mask_boxes: Optional[List[List[float]]] = None
    # Only applies inside the mask, which is why it can be this high. Ignored
    # entirely when mask_boxes is absent — prompt_strength governs there.
    mask_strength: float = 0.95


@app.get("/health")
def health():
    return {
        "status": "ok",
        "base": BASE_MODEL,
        "lora": LORA_READY,
        "lora_file": LORA_FILE,
        "scale_mode": SCALE_MODE,
        # False means this notebook predates masking or failed to build the
        # pipeline, so nail previews will come out unmasked.
        "inpaint": inpaint is not None,
    }


@app.post("/generate")
def generate(req: GenerateRequest):
    """Contract the BeautyCore provider expects: {image: "<base64 png>"}."""
    try:
        out = render(
            req.prompt,
            image=_decode(req.image) if req.image else None,
            strength=req.prompt_strength,
            scale=req.lora_scale,
            steps=req.num_inference_steps,
            guidance=req.guidance_scale,
            mask_boxes=req.mask_boxes,
            mask_strength=req.mask_strength,
        )
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        return {"image": base64.b64encode(buf.getvalue()).decode()}

    except Exception as e:
        # Returned as 200 with an error field; the Next.js provider surfaces
        # this as a friendly message rather than a stack trace.
        return {"error": f"{type(e).__name__}: {e}"}


# --- Cell 5: expose it -----------------------------------------------------
threading.Thread(
    target=lambda: uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning"),
    daemon=True,
).start()
time.sleep(3)

proc = subprocess.Popen(
    ["./cloudflared", "tunnel", "--url", "http://localhost:8000", "--no-autoupdate"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
)

print("Opening tunnel...")
for line in proc.stdout:
    m = re.search(r"https://[-\w]+\.trycloudflare\.com", line)
    if m:
        print("\n" + "=" * 68)
        print("  PUBLIC URL:", m.group(0))
        print("=" * 68)
        print("\n  Put this in beautycore/.env.local:\n")
        print("    PREVIEW_PROVIDER=lora")
        print(f"    LORA_ENDPOINT_URL={m.group(0)}")
        print("\n  Then restart `npm run dev`. Keep this notebook running.")
        print("=" * 68)
        break
