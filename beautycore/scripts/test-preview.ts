/**
 * Render one preview through the exact path the app uses, from the terminal.
 *
 *   npx tsx scripts/test-preview.ts photo.jpg
 *   npx tsx scripts/test-preview.ts photo.jpg out.png
 *   npx tsx scripts/test-preview.ts photo.jpg out.png --prompt "burgundy chrome nails"
 *
 * The browser path needs a login, a running dev server and three clicks, and it
 * hides the two numbers that decide whether a preview worked: how many nails
 * were found, and which strength was used. This prints both, reports whether
 * the notebook on the other end can even do masking, and writes the PNG to disk.
 *
 * Without --prompt it runs the real Gemini analysis and uses the first
 * recommendation's generationPrompt, so this tests what the app actually sends
 * rather than a hand-written approximation.
 *
 * Requires LORA_ENDPOINT_URL in .env.local — the tunnel from the Colab notebook.
 */
import * as dotenv from 'dotenv';
dotenv.config({ path: '.env.local', quiet: true });

import { readFileSync, writeFileSync } from 'node:fs';
import { extname, basename } from 'node:path';

// Imported after dotenv, because these modules read process.env at load time
// (ANALYSIS_MODEL is a module-level const).
const { detectNailBoxes } = await import('../lib/ai/detect.js');
const { analyzePhoto } = await import('../lib/ai/gemini.js');
const { decodeImageInput } = await import('../lib/ai/types.js');

const argv = process.argv.slice(2);
const flagAt = argv.indexOf('--prompt');
const promptOverride = flagAt >= 0 ? argv[flagAt + 1] : undefined;
const positional = argv.filter(
  (a, i) => !a.startsWith('--') && !(flagAt >= 0 && i === flagAt + 1)
);
const [file, outArg] = positional;

if (!file) {
  console.error(
    'Usage: npx tsx scripts/test-preview.ts <photo> [out.png] [--prompt "..."]'
  );
  process.exit(1);
}

const endpoint = process.env.LORA_ENDPOINT_URL?.replace(/\/+$/, '');
if (!endpoint) {
  console.error(
    'LORA_ENDPOINT_URL missing from .env.local.\n' +
      'Run the Colab notebook and paste the printed trycloudflare.com URL.'
  );
  process.exit(1);
}

const MIME: Record<string, string> = {
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.webp': 'image/webp',
};

const out = outArg ?? `${basename(file, extname(file))}-preview.png`;
const buf = readFileSync(file);
const { base64, mimeType } = decodeImageInput(
  `data:${MIME[extname(file).toLowerCase()] ?? 'image/jpeg'};base64,${buf.toString('base64')}`
);

console.log(`\nphoto:    ${file} (${buf.length.toLocaleString()} bytes)`);
console.log(`endpoint: ${endpoint}`);

// ─── Is the far end capable of masking at all? ──────────────────────────────

let serverCanMask = false;
try {
  const health = (await (await fetch(`${endpoint}/health`)).json()) as {
    lora?: boolean;
    inpaint?: boolean;
    base?: string;
  };
  serverCanMask = health.inpaint === true;
  console.log(
    `health:   lora=${health.lora} inpaint=${health.inpaint ?? 'absent'} ` +
      `base=${health.base}`
  );
  if (!health.lora) {
    console.log('\n⚠ The notebook is serving the BASE model — no LoRA loaded.');
  }
  if (health.inpaint === undefined) {
    console.log(
      '\n⚠ No `inpaint` field: that notebook predates masking. It will ignore\n' +
        '  mask_boxes and fall back to unmasked img2img. Re-upload\n' +
        '  scripts/BeautyCore_LoRA_Colab.ipynb to Colab.'
    );
  }
} catch (err) {
  console.error(
    `\n✗ Could not reach ${endpoint}/health — ${err instanceof Error ? err.message : err}`
  );
  console.error('  Is the notebook still running? Tunnel URLs die on restart.');
  process.exit(1);
}

// ─── Detect ─────────────────────────────────────────────────────────────────

const boxes = await detectNailBoxes(base64, mimeType);

console.log(`\n${boxes.length} nail(s) detected`);
for (const [ymin, xmin, ymax, xmax] of boxes) {
  const pct = (((ymax - ymin) * (xmax - xmin)) / (1000 * 1000)) * 100;
  console.log(
    `  [${ymin}, ${xmin}, ${ymax}, ${xmax}]`.padEnd(34) + `${pct.toFixed(2)}% of frame`
  );
}
if (boxes.length === 0) {
  console.log('  → no mask. This will render as unmasked img2img, i.e. the old');
  console.log('    behaviour: expect the rings to change more than the nails.');
}

// ─── Prompt ─────────────────────────────────────────────────────────────────

let prompt = promptOverride;
if (!prompt) {
  console.log('\nAnalysing to get a real generationPrompt...');
  const { analysis } = await analyzePhoto(base64, mimeType);
  const rec = analysis.recommendations[0];
  console.log(`category: ${analysis.category}`);
  console.log(`style:    ${rec.title}`);
  prompt = rec.generationPrompt;
}
console.log(`\nprompt:   ${prompt}`);

// ─── Render ─────────────────────────────────────────────────────────────────

// Mirrors lib/ai/preview.ts. prompt_strength stays low because it governs the
// whole frame; mask_strength is high because it only applies inside the mask.
const promptStrength = 0.5;
const maskStrength = Number(process.env.LORA_MASK_STRENGTH ?? '0.95');
const loraScale = Number(process.env.LORA_SCALE ?? '0.8');

console.log(
  boxes.length
    ? `render:   inpainting ${boxes.length} nail(s) @ ${maskStrength}, lora_scale ${loraScale}`
    : `render:   unmasked img2img @ ${promptStrength}, lora_scale ${loraScale}`
);
console.log('          (first render on a cold GPU can take a minute)\n');

const controller = new AbortController();
const timer = setTimeout(() => controller.abort(), 180_000);

try {
  const res = await fetch(`${endpoint}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal: controller.signal,
    body: JSON.stringify({
      prompt,
      image: `data:${mimeType};base64,${base64}`,
      prompt_strength: promptStrength,
      mask_boxes: boxes.length ? boxes : undefined,
      mask_strength: maskStrength,
      lora_scale: loraScale,
    }),
  });

  if (!res.ok) {
    console.error(`✗ HTTP ${res.status} from the style model.`);
    process.exit(1);
  }

  const data = (await res.json()) as { image?: string; error?: string };

  if (data.error) {
    console.error(`✗ The server reported: ${data.error}`);
    process.exit(1);
  }
  if (!data.image) {
    console.error('✗ No image in the response.');
    process.exit(1);
  }

  const png = data.image.includes(',') ? data.image.split(',', 2)[1] : data.image;
  writeFileSync(out, Buffer.from(png, 'base64'));

  console.log(`✓ wrote ${out}\n`);
  console.log(`Open it next to ${file} and check both halves of the claim:`);
  console.log('  1. the NAILS changed colour/finish');
  console.log('  2. rings, skin and background are IDENTICAL to the original');
  if (boxes.length && !serverCanMask) {
    console.log('\n⚠ Boxes were sent but that notebook cannot mask, so 2. will fail.');
  }
  console.log();
} catch (err) {
  const aborted = err instanceof Error && err.name === 'AbortError';
  console.error(
    aborted
      ? '✗ Timed out after 180s. The Colab GPU may still be loading — retry.'
      : `✗ ${err instanceof Error ? err.message : err}`
  );
  process.exit(1);
} finally {
  clearTimeout(timer);
}
