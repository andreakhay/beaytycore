'use client';

import StudioPage, {
  type PresetDesign,
  type BuilderGroup,
} from '@/components/StudioPage';

const presets: PresetDesign[] = [
  {
    id: 'soft-rose-almond',
    name: 'Soft Rose Almond',
    description: 'Glossy dusty-rose gel on an almond shape, with a single pearl accent nail.',
    tags: ['Almond', 'Gel', 'Minimal'],
    price: 750,
    gradient: 'linear-gradient(135deg, #d9a7ab, #b5787f)',
  },
  {
    id: 'milky-glazed',
    name: 'Milky Glazed',
    description: 'Sheer milky base finished with an iridescent chrome glaze.',
    tags: ['Chrome', 'Sheer', 'Low-maintenance'],
    price: 800,
    gradient: 'linear-gradient(135deg, #f3e7ef, #cbb8d4)',
  },
  {
    id: 'emerald-chrome',
    name: 'Emerald Chrome',
    description: 'Full chrome coverage in deep emerald with scattered gold foil.',
    tags: ['Coffin', 'Chrome', 'Statement'],
    price: 1100,
    gradient: 'linear-gradient(135deg, #0f6b52, #d4af37)',
  },
  {
    id: 'micro-french',
    name: 'Micro French',
    description: 'An ultra-thin white tip over a sheer pink base — the modern French.',
    tags: ['Square', 'Classic', 'Subtle'],
    price: 650,
    gradient: 'linear-gradient(135deg, #f7e9ec, #ffffff)',
  },
  {
    id: 'midnight-velvet',
    name: 'Midnight Velvet',
    description: 'Magnetic cat-eye in deep plum with silver chrome detailing.',
    tags: ['Cat-eye', 'Dark', 'Textured'],
    price: 1200,
    gradient: 'linear-gradient(135deg, #3b1f45, #8b6f9e)',
  },
  {
    id: 'stiletto-ombre',
    name: 'Stiletto Ombré',
    description: 'Sapphire-to-clear ombré on a sculpted stiletto extension.',
    tags: ['Stiletto', 'Ombré', 'Extensions'],
    price: 1400,
    gradient: 'linear-gradient(135deg, #1b3a6b, #7fa8d4)',
  },
];

const builder: BuilderGroup[] = [
  {
    key: 'shape',
    label: 'Shape',
    options: [
      { id: 'round', label: 'Round', price: 0 },
      { id: 'square', label: 'Square', price: 0 },
      { id: 'almond', label: 'Almond', price: 80 },
      { id: 'coffin', label: 'Coffin', price: 120 },
      { id: 'stiletto', label: 'Stiletto', price: 150 },
    ],
  },
  {
    key: 'colour',
    label: 'Colour',
    options: [
      { id: 'nude', label: 'Warm Nude', price: 0, swatch: '#d8b8a0' },
      { id: 'rose', label: 'Dusty Rose', price: 0, swatch: '#c98b93' },
      { id: 'milky', label: 'Milky White', price: 0, swatch: '#f0e6ec' },
      { id: 'emerald', label: 'Emerald', price: 60, swatch: '#0f6b52' },
      { id: 'sapphire', label: 'Sapphire', price: 60, swatch: '#1b3a6b' },
      { id: 'plum', label: 'Deep Plum', price: 60, swatch: '#4a2352' },
    ],
  },
  {
    key: 'finish',
    label: 'Finish',
    options: [
      { id: 'gloss', label: 'High Gloss', price: 0 },
      { id: 'matte', label: 'Matte', price: 50 },
      { id: 'chrome', label: 'Chrome', price: 180 },
      { id: 'velvet', label: 'Magnetic Velvet', price: 220 },
    ],
  },
  {
    key: 'art',
    label: 'Nail Art',
    options: [
      { id: 'none', label: 'None', price: 0 },
      { id: 'accent', label: 'Single Accent', price: 100 },
      { id: 'french', label: 'French Tips', price: 150 },
      { id: 'foil', label: 'Gold Foil', price: 200 },
      { id: 'handpaint', label: 'Hand-painted', price: 350 },
    ],
  },
];

export default function NailStudio() {
  return (
    <StudioPage
      title="Nail Studio"
      subtitle="Browse our designs, or build your own and see the price update as you go."
      bookingHref="/booking?service=nail-studio"
      basePrice={350}
      presets={presets}
      builder={builder}
    />
  );
}
