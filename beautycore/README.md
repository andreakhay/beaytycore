# BeautyCore — Andrea's Salon Management System

An AI-assisted salon platform: clients upload a photo, Google Gemini analyses
their current hair or nails and recommends styles grounded in what it actually
sees. Staff manage bookings, inventory, and finances from role-scoped portals.

Built with Next.js 16 (App Router), React 19, TypeScript (strict), Tailwind 4,
Drizzle ORM, and Neon PostgreSQL.

---

## Quick start

```bash
npm install
cp .env.local.example .env.local   # then fill in your keys
npm run db:push                    # create tables
npm run db:seed                    # load demo data
npm run dev                        # http://localhost:3000
```

`db:seed` is idempotent — it clears and reloads demo rows, so you can run it
whenever you want a clean slate.

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Admin | `admin@andreas.com` | `admin123` |
| Stylist | `lara@andreas.com` | `stylist123` |
| Client | `maria@email.com` | `client123` |

Seeded with 9 users, 14 appointments, 18 inventory products, and 5 AI records.

---

## Architecture

```
app/
  (public)/          home, services, about, contact, booking
  (auth)/            login, register
  client/            dashboard, ai-advisor, nail/hair studio, appointments, profile
  admin/             dashboard, appointments, clients, inventory, finance,
                     market-trends, security
  stylist/           dashboard, appointments, clients, services, profile
  api/               auth, appointments, inventory, users, profile,
                     analyze, generate, generations, admin/stats
components/          ui.tsx (shared primitives), sidebars, navbar, footer
context/             AuthContext
db/                  schema.ts, index.ts, seed.ts
lib/                 auth.ts, services.ts, ai/
scripts/             BeautyCore_LoRA_Colab.ipynb, colab_lora_server.py,
                     tsx diagnostics (see Scripts below)
```

**Auth** — bcrypt password hashing, JWT in an HttpOnly cookie (`jose`), 7-day
expiry. `getSession()` / `requireRole()` guard every protected route handler.
Role checks live server-side; `ProtectedRoute` only handles redirects.

**Data scoping** — the same `/api/appointments` endpoint returns different rows
per role: clients see their own, stylists see those assigned to them, admins see
everything. Scoping happens in the query, not the UI.

---

## The AI pipeline

Two stages, deliberately separated:

1. **Analysis** (`/api/analyze`) — Gemini vision reads the photo and returns the
   current shape, colour, and condition, plus three recommendations with colour
   palettes, design details, reasoning, and a generation prompt. This is fully
   live and the part your capstone demo rests on.

2. **Preview** (`/api/generate`) — renders a recommendation onto the client's
   photo. Provider-swappable via `PREVIEW_PROVIDER`:

   | Value | Behaviour |
   |---|---|
   | `stub` *(default)* | No image. Analysis still works; the UI explains why. |
   | `lora` | Calls your own LoRA over HTTP. See below. |
   | `gemini` | Google image models — **needs a billed Google Cloud account.** |

Every generation is persisted to `ai_generations` regardless of whether a
preview rendered, so the analysis is never lost.

### Wiring up the LoRA

The trained model is a **Stable Diffusion 1.5** LoRA (rank 32, 512px, 1500
steps), trained with the diffusers `train_text_to_image_lora.py` script. It is
UNet-only — no text encoder weights.

`scripts/BeautyCore_LoRA_Colab.ipynb` turns a Colab notebook into an
image-to-image endpoint for it:

1. Upload the notebook to [colab.research.google.com](https://colab.research.google.com)
   (**File → Upload notebook**), then set **Runtime → Change runtime type → T4 GPU**
2. Upload `pytorch_lora_weights.safetensors` (or mount Drive and point
   `LORA_PATH` at the model folder), then run the cells in order
3. **Run the smoke-test cell and look at the output.** Training used
   `validation_prompt: null`, so no sample image was produced during those 1500
   steps — the smoke test is the first look anyone gets. It sweeps LoRA scale
   and asserts the output actually differs with the LoRA off vs on, which
   catches a LoRA that loads but never reaches the UNet.
4. Copy the printed `https://….trycloudflare.com` URL
5. Add to `.env.local` and restart:
   ```
   PREVIEW_PROVIDER=lora
   LORA_ENDPOINT_URL=https://your-tunnel.trycloudflare.com
   ```

The tunnel URL changes on every Colab restart — re-paste it each session.

#### Starting a session from scratch

Two halves have to be running at once: Colab holds the GPU, your machine holds
the app. Colab is the one that dies overnight.

**1. Colab** — open the notebook, **Runtime → Change runtime type → T4 GPU**, then
run cells **1, 2, 4, 5** in order. Cell 3 is an optional smoke test; skip it
unless something looks wrong.

Two lines to check as they run:

- Cell 2 must print `✓ Inpainting pipeline ready`. If it prints the
  `⚠ INPAINTING UNAVAILABLE` banner, run `!pip install -U diffusers` and re-run
  the cell — otherwise previews silently fall back to the old unmasked path.
- Cell 5 prints `PUBLIC URL: https://….trycloudflare.com`. Cell 5 then sits
  there forever, which is correct — it is holding the tunnel open.

**2. Your machine** — paste that URL into `.env.local`:

```
PREVIEW_PROVIDER=lora
LORA_ENDPOINT_URL=https://whatever-cell-5-printed.trycloudflare.com
```

**3. Restart the dev server.** Next.js reads env at startup, so a URL pasted
while it is already running has no effect. Ctrl-C, then `npm run dev`.

Then log in as `maria@email.com` / `client123` → AI Advisor → upload a nail
photo → analyse → generate a preview.

**When previews stop working,** it is almost always a dead tunnel — Colab
disconnects after idling. Check it directly:

```bash
curl https://your-tunnel.trycloudflare.com/health
```

`{"lora":true,"inpaint":true,...}` means the GPU side is fine and the problem is
local. Anything else — timeout, 502, no response — means re-run Cell 5 for a new
URL and repeat steps 2 and 3.

The terminal logs one line per render. `inpainting 5 nail(s) @ strength 0.95` is
the healthy case; `unmasked img2img` means detection found no nails and the
render fell back, which is worth investigating on that photo.

### How nail masking works

Previews are rendered as **masked inpainting**, not plain image-to-image, and
this is the difference between a preview that works and one that doesn't.

Image-to-image adds noise uniformly across the frame. A fingernail is roughly 1%
of a hand photo, so the model spends its change budget wherever there is room —
in testing it reliably replaced a ring and left the nails untouched, even with a
prompt asking for burgundy on pale pink nails.

So before rendering, `lib/ai/detect.ts` asks Gemini for one bounding box per nail
and sends them to the LoRA server, which rasterises them into a blurred mask
(`build_mask` in the notebook) and repaints only inside it. Confined that way,
strength can go to 0.95 — high enough for a genuine colour change — while rings,
skin and background are untouched by construction.

Two safeguards, because a wrong mask is worse than no mask:

- Boxes are validated and clamped, and the **whole set is discarded if it covers
  more than 60% of the frame** — that means detection boxed the hand, not the
  nails, and repainting through it at 0.95 would wreck the photo.
- Detection never throws. No API key, a quota error, or no nails found all return
  no boxes, and the render falls back to the old unmasked path.

Hair is unaffected: a box mask can't describe hair, and `LORA_STYLE_SCOPE`
already refuses hair requests.

Tuning knobs, all optional (full comments in `.env.local.example`):

| Variable | Default | Effect |
|---|---|---|
| `LORA_SCALE` | `0.8` | How strongly the trained style is applied |
| `LORA_MASK_STRENGTH` | `0.95` | How much of each nail may be repainted |
| `LORA_NAIL_MASK` | `1` | Set `0` to force the old unmasked path, for comparison |

Mask *geometry* — how far each box is padded and how much the edge is feathered —
lives in the notebook as `MASK_PAD` / `MASK_BLUR`, not in env vars, because it is
tuned by looking at the overlay the smoke test prints.

Notes worth knowing:

- **An old notebook silently degrades.** If Colab is still running a copy from
  before this change, it ignores `mask_boxes` and renders unmasked — so previews
  look like the old broken ones with no error anywhere. `GET /health` on the
  tunnel reports `"inpaint": true` when the running notebook can mask; the
  `inpaint` field is simply absent on older ones.
- **It's SD 1.5, not SDXL.** Serving it on an SDXL base fails outright: this
  LoRA's cross-attention layers are 768-dim against SDXL's 2048.
- **The base model id in `hparams.yml` is dead.** Runway deleted their
  HuggingFace repos, so `runwayml/stable-diffusion-v1-5` now 404s. The script
  tries the surviving mirrors of the same weights in order.
- **The NSFW safety checker is disabled deliberately.** SD 1.5's checker
  false-positives on close-up skin — hands and faces, i.e. this app's only
  input — and returns a solid black image instead of an error.
- **`LORA_STYLE_SCOPE` defaults to `nails`,** matching the model that exists.
  A nails LoRA applied to a hair photo produces nonsense, so hair requests get
  an honest "not available yet" instead. Widen it to `hair,nails` once a hair
  LoRA is trained.
- **Upload the top-level `pytorch_lora_weights.safetensors`,** not one from a
  `checkpoint-*` folder. The top-level file is the finished 1500-step export in
  diffusers key naming; the checkpoints hold the same weights under PEFT naming
  (`lora_A`/`lora_B`). The notebook converts PEFT keys automatically, so
  pointing `LORA_PATH` at `checkpoint-1000` to compare training stages does
  work — but the top-level file is the one to start with.
- **Checkpoints at 500/1000/1500 steps** are in the model folder. 1500 is the
  default; warmup ran for the first 500, so `checkpoint-500` is undertrained.
  If 1500 looks overcooked, compare against `checkpoint-1000`.

The notebook is generated from `scripts/colab_lora_server.py`, which is the
readable source of truth. If you edit the script, regenerate with:

```bash
py scripts/make_notebook.py scripts/colab_lora_server.py scripts/BeautyCore_LoRA_Colab.ipynb
```

---

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server (Turbopack) |
| `npm run build` | Production build |
| `npm run start` | Serve the build |
| `npm run lint` | ESLint |
| `npm run db:push` | Push schema to Neon |
| `npm run db:seed` | Reset and load demo data |
| `npm run db:studio` | Drizzle Studio (browse the DB) |

### Diagnostics

Not npm scripts — run them directly. All read `.env.local`, none need a dev
server or a login, which makes them the fastest way to find out which stage of
the pipeline is misbehaving.

| Command | What it tells you |
|---|---|
| `npx tsx scripts/test-analyze.ts <photo>` | Whether Gemini analysis works at all |
| `npx tsx scripts/show-prompts.ts <photo>` | The full, untruncated prompts the LoRA will receive |
| `npx tsx scripts/nail-boxes.ts <photo>` | Where Gemini thinks the nails are, plus a paste-ready `NAIL_BOXES` line for the notebook |
| `npx tsx scripts/test-preview.ts <photo> [out.png]` | End-to-end render: box count, strength used, whether the notebook can mask, and the PNG on disk |

`test-preview.ts` is the one that answers "is the preview actually fixed" — open
its output next to the original and check that the nails changed and the rings
did not.

## Notes

- `_legacy_src/` holds the original Vite + React Router code, kept because this
  project isn't under version control. Nothing imports from it; delete it once
  you're confident in the migration.
- Prices are stored as whole pesos in `integer` columns — no floating-point
  rounding on money.
- Services marked *Mula* (from) vary by hair length and condition.
