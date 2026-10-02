import { GoogleGenAI, Type } from '@google/genai';
import type { StyleAnalysis } from './types';

/**
 * Model note: several `gemini-2.5-*` ids are closed to new API keys and 404.
 * `gemini-flash-latest` is an alias Google keeps pointed at a current model,
 * so it survives deprecations. Override with GEMINI_MODEL if needed.
 */
export const ANALYSIS_MODEL = process.env.GEMINI_MODEL ?? 'gemini-flash-latest';

let client: GoogleGenAI | null = null;

export function getGemini(): GoogleGenAI {
  if (!process.env.GEMINI_API_KEY) {
    throw new Error(
      'GEMINI_API_KEY is not set. Add it to .env.local — see .env.local.example.'
    );
  }
  client ??= new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
  return client;
}

/** Structured-output schema. Forces exactly the shape StyleAnalysis expects. */
const analysisSchema = {
  type: Type.OBJECT,
  properties: {
    category: {
      type: Type.STRING,
      enum: ['hair', 'nails'],
      description: 'Whether the photo primarily shows hair or nails.',
    },
    currentAttributes: {
      type: Type.OBJECT,
      properties: {
        shapeOrCut: { type: Type.STRING, description: 'Current shape or cut.' },
        color: { type: Type.STRING, description: 'Current colour or tone.' },
        condition: { type: Type.STRING, description: 'Visible condition and health.' },
      },
      required: ['shapeOrCut', 'color', 'condition'],
    },
    recommendations: {
      type: Type.ARRAY,
      minItems: 3,
      maxItems: 3,
      items: {
        type: Type.OBJECT,
        properties: {
          title: { type: Type.STRING, description: 'Short, appealing style name.' },
          colorPalette: { type: Type.STRING, description: 'Comma-separated colours.' },
          designDetails: { type: Type.STRING, description: 'Shape, finish, technique.' },
          reasoning: {
            type: Type.STRING,
            description: 'Why this suits THIS photo specifically.',
          },
          generationPrompt: {
            type: Type.STRING,
            description:
              'Self-contained photorealistic image prompt for this style. No names or references to the analysis.',
          },
        },
        required: ['title', 'colorPalette', 'designDetails', 'reasoning', 'generationPrompt'],
      },
    },
  },
  required: ['category', 'currentAttributes', 'recommendations'],
} as const;

const SYSTEM_PROMPT = `You are a senior stylist at Andrea's Aesthetic & Wellness Clinic, a premium hair and nail salon.

A client has uploaded a photo. Your job:

1. Decide whether the photo primarily shows HAIR or NAILS.
2. Describe what you actually observe — current shape/cut, colour, and condition. Be specific and honest about what is visible; do not invent detail you cannot see.
3. Propose exactly THREE distinct style recommendations that would genuinely suit this client.

Rules for recommendations:
- They must be meaningfully different from each other, not three shades of one idea.
- Ground each "reasoning" in something visible in the photo (length, tone, nail bed shape, face framing, condition). Reference the actual photo, not generic advice.
- Respect what is realistically achievable from the current state. Do not propose a platinum transformation on virgin black hair as if it were a single session.
- "generationPrompt" must be a standalone photorealistic prompt describing the finished look — salon photography, good lighting, high detail. It must not mention the client, the analysis, or the words "recommendation"/"option".

Be warm and professional. This text is shown directly to the client.`;

export interface AnalyzeResult {
  analysis: StyleAnalysis;
  model: string;
}

/** Runs vision analysis on an uploaded photo. */
export async function analyzePhoto(
  base64: string,
  mimeType: string
): Promise<AnalyzeResult> {
  const ai = getGemini();

  const response = await ai.models.generateContent({
    model: ANALYSIS_MODEL,
    contents: [
      {
        role: 'user',
        parts: [
          { inlineData: { mimeType, data: base64 } },
          { text: 'Analyse this photo and give me three style recommendations.' },
        ],
      },
    ],
    config: {
      systemInstruction: SYSTEM_PROMPT,
      responseMimeType: 'application/json',
      responseSchema: analysisSchema,
      temperature: 0.9, // some variety across repeat uploads
    },
  });

  const raw = response.text;
  if (!raw) {
    throw new Error('The AI returned an empty response. Please try again.');
  }

  let parsed: StyleAnalysis;
  try {
    parsed = JSON.parse(raw) as StyleAnalysis;
  } catch {
    throw new Error('The AI returned malformed data. Please try again.');
  }

  // The schema should guarantee this, but a bad response shouldn't reach the UI.
  if (
    !parsed?.category ||
    !parsed.currentAttributes ||
    !Array.isArray(parsed.recommendations) ||
    parsed.recommendations.length === 0
  ) {
    throw new Error('The AI response was incomplete. Please try again.');
  }

  return { analysis: parsed, model: ANALYSIS_MODEL };
}
