/**
 * Ask Gemini for a bounding box around every fingernail in a photo.
 *   npx tsx scripts/nail-boxes.ts path/to/photo.jpg
 *
 * Plain img2img has no spatial control: it repaints the whole frame, so it
 * tends to alter rings and background while leaving the nails alone. Boxes
 * from here become an inpainting mask, so only the nails get repainted.
 */
import * as dotenv from 'dotenv';
dotenv.config({ path: '.env.local', quiet: true });

import { readFileSync } from 'node:fs';
import { extname } from 'node:path';
import { GoogleGenAI, Type } from '@google/genai';

const file = process.argv[2];
if (!file) {
  console.error('Usage: npx tsx scripts/nail-boxes.ts <path-to-photo>');
  process.exit(1);
}

const MIME: Record<string, string> = {
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.webp': 'image/webp',
};

const apiKey = process.env.GEMINI_API_KEY;
if (!apiKey) {
  console.error('GEMINI_API_KEY missing from .env.local');
  process.exit(1);
}

const ai = new GoogleGenAI({ apiKey });
const buf = readFileSync(file);

const res = await ai.models.generateContent({
  model: process.env.GEMINI_MODEL ?? 'gemini-flash-latest',
  contents: [
    {
      role: 'user',
      parts: [
        {
          inlineData: {
            mimeType: MIME[extname(file).toLowerCase()] ?? 'image/jpeg',
            data: buf.toString('base64'),
          },
        },
        {
          text:
            'Detect every visible fingernail in this photo, including the ' +
            'thumbnail. For each, give box_2d as [ymin, xmin, ymax, xmax] ' +
            'normalised to 0-1000, tight to the nail plate only. Do not ' +
            'include fingers, skin, rings, or jewellery.',
        },
      ],
    },
  ],
  config: {
    responseMimeType: 'application/json',
    responseSchema: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          label: { type: Type.STRING },
          box_2d: { type: Type.ARRAY, items: { type: Type.NUMBER } },
        },
        required: ['label', 'box_2d'],
      },
    },
  },
});

const boxes = JSON.parse(res.text ?? '[]') as { label: string; box_2d: number[] }[];

console.log(`\n${boxes.length} nail(s) detected in ${file}\n`);
for (const b of boxes) {
  const [ymin, xmin, ymax, xmax] = b.box_2d;
  console.log(
    `  ${b.label.padEnd(22)} [${ymin}, ${xmin}, ${ymax}, ${xmax}]` +
      `   ${((xmax - xmin) / 10).toFixed(1)}% x ${((ymax - ymin) / 10).toFixed(1)}% of frame`
  );
}

console.log('\nPaste into the Colab notebook:\n');
console.log(`NAIL_BOXES = ${JSON.stringify(boxes.map((b) => b.box_2d))}`);
console.log();
