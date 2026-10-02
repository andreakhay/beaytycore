"""Convert the cell-marked .py serving script into a real Colab notebook."""
import json, re, sys

src_path, out_path = sys.argv[1], sys.argv[2]
lines = open(src_path, encoding="utf-8").read().split("\n")

# The file opens with a banner comment block, then `# --- Cell N: title ---`
# markers. Split on those; the banner becomes a markdown cell.
marker = re.compile(r"^# --- Cell \d+: (.+?) -+$")

blocks, current, header = [], [], []
for line in lines:
    m = marker.match(line)
    if m:
        if current:
            blocks.append(current)
        elif not blocks:
            header = current
        current = []
        continue
    current.append(line)
if current:
    blocks.append(current)

if not blocks:
    sys.exit("No cell markers found — nothing to convert.")

# Everything before the first marker is the banner.
if header == [] and blocks:
    header, blocks = blocks[0], blocks[1:]

titles = [m.group(1) for m in (marker.match(l) for l in lines) if m]


def strip_blanks(xs):
    while xs and not xs[0].strip():
        xs.pop(0)
    while xs and not xs[-1].strip():
        xs.pop()
    return xs


def src(xs):
    """nbformat wants a list of lines, each keeping its trailing newline."""
    xs = strip_blanks(list(xs))
    return [l + "\n" for l in xs[:-1]] + ([xs[-1]] if xs else [])


cells = []

# A comment banner converted mechanically to markdown reads badly (setext
# underlines, stray indents), and this is the first thing anyone sees. Author it.
INTRO = """## BeautyCore — LoRA preview server (Stable Diffusion 1.5)

Serves the trained BeautyCore LoRA over HTTP so the Next.js app can render
style previews onto a client's own photo.

**The model this targets**, read from `logs/text2image-fine-tune/*/hparams.yml`:

| setting | value |
|---|---|
| base model | `runwayml/stable-diffusion-v1-5` |
| resolution | 512 |
| LoRA rank | 32 (UNet only, no text encoder) |
| training steps | 1500 — checkpoints at 500 / 1000 / 1500 |
| `validation_prompt` | `null` — **never validated during training** |

This is **SD 1.5, not SDXL.** Serving it on an SDXL base fails outright: these
cross-attention layers are 768-dim against SDXL's 2048.

### How to run

1. **Runtime → Change runtime type → T4 GPU**, then run the cells in order.
2. Upload `pytorch_lora_weights.safetensors` to `/content/`, or mount Drive and
   point `LORA_PATH` at the `BeautyCore_Model` folder.
3. Run cells 1 → 2 → 3 and **look at the smoke test output.** Training produced
   no sample images, so that cell is the first time anyone sees what this model
   actually does. It also proves the LoRA is reaching the UNet rather than
   loading and sitting inert.
4. Optional but worth it: upload one real photo as `/content/test.jpg` first.
   Cell 3 will then preview the exact image-to-image path the app uses.
5. Copy the tunnel URL printed by the last cell into `beautycore/.env.local`:
   ```
   PREVIEW_PROVIDER=lora
   LORA_ENDPOINT_URL=https://....trycloudflare.com
   ```
   Then restart `npm run dev`.

### Keep in mind

- The tunnel URL **changes every time this notebook restarts** — re-paste it.
- Keep this tab open and the runtime alive for the whole demo.
- Free-tier Colab reclaims idle GPUs; interact with the page occasionally.
- `LORA_STYLE_SCOPE` in `.env.local` defaults to `nails`. Widen it to
  `hair,nails` only once a hair LoRA actually exists — the nails model applied
  to a hair photo produces nonsense.
"""

cells.append({"cell_type": "markdown", "metadata": {}, "source": src(INTRO.split("\n"))})

# Nicer section headings than the raw markers ("install" -> "1 · Install").
PRETTY = {
    "install": "1 · Install dependencies",
    "load the pipeline": "2 · Load SD 1.5 and apply the LoRA",
    "the API": "4 · Serve it over HTTP",
    "expose it": "5 · Open a public tunnel",
}

for title, body in zip(titles, blocks):
    body = strip_blanks(list(body))
    if not body:
        continue
    key = title.strip()
    if key.lower().startswith("smoke test"):
        heading = "3 · Smoke test — run this and actually look at it"
    else:
        heading = PRETTY.get(key, key)
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": src([f"### {heading}"]),
    })
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": src(body),
    })

notebook = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {
        "colab": {"provenance": [], "gpuType": "T4"},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
        "accelerator": "GPU",
    },
    "cells": cells,
}

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)
    f.write("\n")

code_cells = sum(1 for c in cells if c["cell_type"] == "code")
print(f"Wrote {out_path}: {len(cells)} cells ({code_cells} code)")
for t in titles:
    print(f"  - {t.strip()}")
