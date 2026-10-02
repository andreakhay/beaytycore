'use client';

import StudioPage, {
  type PresetDesign,
  type BuilderGroup,
} from '@/components/StudioPage';

const presets: PresetDesign[] = [
  {
    id: 'caramel-balayage',
    name: 'Caramel Balayage',
    description: 'Hand-painted caramel through the mid-lengths with soft, face-framing layers.',
    tags: ['Balayage', 'Warm', 'Low upkeep'],
    price: 1500,
    gradient: 'linear-gradient(135deg, #6b4423, #c99b6a)',
  },
  {
    id: 'glass-hair',
    name: 'Mirror Glass Hair',
    description: 'Pin-straight, high-gloss finish with a seamless shadow root.',
    tags: ['Sleek', 'Gloss', 'Straight'],
    price: 1200,
    gradient: 'linear-gradient(135deg, #2c2c34, #8f9ba8)',
  },
  {
    id: 'money-piece',
    name: 'Golden Money Piece',
    description: 'Two bright face-framing panels over your natural base.',
    tags: ['Highlights', 'Face-framing', 'Quick'],
    price: 900,
    gradient: 'linear-gradient(135deg, #2b2118, #e0c27f)',
  },
  {
    id: 'textured-shag',
    name: 'Textured Shag',
    description: 'Choppy layers with piecey texture — great for growing out a short cut.',
    tags: ['Cut', 'Texture', 'Editorial'],
    price: 650,
    gradient: 'linear-gradient(135deg, #1f1a24, #5c4f63)',
  },
  {
    id: 'chocolate-gloss',
    name: 'Chocolate Gloss',
    description: 'All-over gloss with a warm red undertone and a blunt perimeter.',
    tags: ['Colour', 'Shine', 'Rich'],
    price: 1100,
    gradient: 'linear-gradient(135deg, #3b2314, #8a4b2a)',
  },
  {
    id: 'keratin-smooth',
    name: 'Keratin Smoothing',
    description: 'Frizz-eliminating treatment that lasts through several months of humidity.',
    tags: ['Treatment', 'Smoothing', 'Long-lasting'],
    price: 2500,
    gradient: 'linear-gradient(135deg, #4a3f52, #b9a8c4)',
  },
];

const builder: BuilderGroup[] = [
  {
    key: 'service',
    label: 'Service',
    options: [
      { id: 'cut', label: 'Cut & Blowdry', price: 0 },
      { id: 'colour', label: 'Full Colour', price: 450 },
      { id: 'highlights', label: 'Highlights', price: 850 },
      { id: 'balayage', label: 'Balayage', price: 1150 },
      { id: 'treatment', label: 'Treatment', price: 800 },
    ],
  },
  {
    key: 'tone',
    label: 'Tone',
    options: [
      { id: 'natural', label: 'Keep Natural', price: 0, swatch: '#3b2a1f' },
      { id: 'caramel', label: 'Caramel', price: 0, swatch: '#c99b6a' },
      { id: 'ash', label: 'Ash Blonde', price: 120, swatch: '#b9b3aa' },
      { id: 'chocolate', label: 'Chocolate', price: 0, swatch: '#4a2c1a' },
      { id: 'burgundy', label: 'Burgundy', price: 120, swatch: '#5c1f2e' },
      { id: 'copper', label: 'Copper', price: 120, swatch: '#a5502a' },
    ],
  },
  {
    key: 'length',
    label: 'Length',
    options: [
      { id: 'short', label: 'Short', price: 0 },
      { id: 'medium', label: 'Medium', price: 150 },
      { id: 'long', label: 'Long', price: 350 },
      { id: 'extra', label: 'Extra Long', price: 550 },
    ],
  },
  {
    key: 'finish',
    label: 'Finishing',
    options: [
      { id: 'blowdry', label: 'Blowdry', price: 0 },
      { id: 'waves', label: 'Glam Waves', price: 200 },
      { id: 'straight', label: 'Sleek Straight', price: 180 },
      { id: 'updo', label: 'Updo', price: 400 },
    ],
  },
];

export default function HairStudio() {
  return (
    <StudioPage
      title="Hair Studio"
      subtitle="Explore cuts, colour, and treatments — or configure your own and price it live."
      bookingHref="/booking?service=hair-design"
      basePrice={350}
      presets={presets}
      builder={builder}
    />
  );
}
