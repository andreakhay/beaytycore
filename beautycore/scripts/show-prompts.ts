/**
 * Print, in full, the prompts Gemini produces for one photo.
 *   npx tsx scripts/show-prompts.ts path/to/photo.jpg
 *
 * Useful when testing the LoRA in Colab: paste a real `generationPrompt` into
 * the notebook rather than a hand-written approximation, so you are testing
 * what the app actually sends. test-analyze.ts truncates prompts to 110 chars
 * because it is checking the contract, not the wording; this one does not.
 */
import * as dotenv from 'dotenv';
dotenv.config({ path: '.env.local', quiet: true });

import { readFileSync } from 'node:fs';
import { extname } from 'node:path';

// Imported dynamically to bypass the server-only guard in a CLI context.
const { analyzePhoto } = await import('../lib/ai/gemini.js');
const { decodeImageInput } = await import('../lib/ai/types.js');

const file = process.argv[2];
if (!file) {
  console.error('Usage: npx tsx scripts/show-prompts.ts <path-to-photo>');
  process.exit(1);
}

const MIME: Record<string, string> = {
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.webp': 'image/webp',
};
const mime = MIME[extname(file).toLowerCase()] ?? 'image/jpeg';

const buf = readFileSync(file);
const { base64, mimeType } = decodeImageInput(
  `data:${mime};base64,${buf.toString('base64')}`
);

const { analysis, model } = await analyzePhoto(base64, mimeType);

console.log(`\nfile:     ${file} (${buf.length.toLocaleString()} bytes)`);
console.log(`model:    ${model}`);
console.log(`category: ${analysis.category}`);
console.log(
  `current:  shape="${analysis.currentAttributes.shapeOrCut}" ` +
    `color="${analysis.currentAttributes.color}" ` +
    `condition="${analysis.currentAttributes.condition}"`
);

analysis.recommendations.forEach((r, i) => {
  console.log(`\n${'='.repeat(72)}`);
  console.log(`${i + 1}. ${r.title}`);
  console.log('='.repeat(72));
  console.log(`palette: ${r.colorPalette}`);
  console.log(`details: ${r.designDetails}`);
  console.log(`why:     ${r.reasoning}`);
  console.log('\ngenerationPrompt — this exact string is what reaches the LoRA:');
  console.log(r.generationPrompt);
});

console.log();
