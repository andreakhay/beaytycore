/**
 * Manual check for the analysis pipeline. Run: npx tsx scripts/test-analyze.ts
 * Hits the real Gemini API with the demo images in public/.
 */
import * as dotenv from 'dotenv';
dotenv.config({ path: '.env.local', quiet: true });

import { readFileSync } from 'node:fs';

// Import dynamically to bypass server-only guard in CLI
const { analyzePhoto } = await import('../lib/ai/gemini.js');
const { decodeImageInput } = await import('../lib/ai/types.js');

async function check(file: string, mime: string) {
  console.log(`\n${'='.repeat(70)}\n${file}\n${'='.repeat(70)}`);

  const buf = readFileSync(`public/${file}`);
  const { base64, mimeType } = decodeImageInput(
    `data:${mime};base64,${buf.toString('base64')}`
  );

  const t0 = Date.now();
  const { analysis, model } = await analyzePhoto(base64, mimeType);
  const secs = ((Date.now() - t0) / 1000).toFixed(1);

  console.log(`model=${model}  time=${secs}s`);
  console.log(`category: ${analysis.category}`);
  console.log(`current:  shape="${analysis.currentAttributes.shapeOrCut}"`);
  console.log(`          color="${analysis.currentAttributes.color}"`);
  console.log(`          condition="${analysis.currentAttributes.condition}"`);
  console.log(`recommendations: ${analysis.recommendations.length}`);

  analysis.recommendations.forEach((r, i) => {
    console.log(`\n  ${i + 1}. ${r.title}`);
    console.log(`     palette:  ${r.colorPalette}`);
    console.log(`     details:  ${r.designDetails}`);
    console.log(`     why:      ${r.reasoning}`);
    console.log(`     prompt:   ${r.generationPrompt.slice(0, 110)}...`);
  });

  // The contract the UI depends on.
  const problems: string[] = [];
  if (analysis.recommendations.length !== 3) problems.push('expected exactly 3 recommendations');
  if (!['hair', 'nails'].includes(analysis.category)) problems.push(`bad category "${analysis.category}"`);
  analysis.recommendations.forEach((r, i) => {
    for (const f of ['title', 'colorPalette', 'designDetails', 'reasoning', 'generationPrompt'] as const) {
      if (!r[f]?.trim()) problems.push(`rec ${i + 1} missing ${f}`);
    }
  });
  const titles = new Set(analysis.recommendations.map((r) => r.title));
  if (titles.size !== analysis.recommendations.length) problems.push('duplicate titles');

  console.log(problems.length ? `\n  ✗ ${problems.join('; ')}` : '\n  ✓ contract satisfied');
  return problems.length === 0;
}

(async () => {
  const results = [
    await check('nails.jpg', 'image/jpeg'),
    await check('hairextension.jpg', 'image/jpeg'),
  ];
  console.log(`\n${'='.repeat(70)}`);
  console.log(results.every(Boolean) ? '✅ All analysis checks passed' : '❌ Some checks failed');
  process.exit(results.every(Boolean) ? 0 : 1);
})().catch((e) => {
  console.error('\n❌ Threw:', e instanceof Error ? e.message : e);
  process.exit(1);
});
