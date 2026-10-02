/**
 * Seed script for BeautyCore — Andrea's Aesthetic & Wellness Clinic
 *
 * Usage:  npm run db:seed
 *
 * Wipes and repopulates all tables with demo data for the capstone
 * presentation. Safe to re-run — it truncates first.
 */
import { db } from './index';
import {
  users,
  clientProfiles,
  appointments,
  inventory,
  aiGenerations,
  type NewUser,
  type NewAppointment,
  type NewInventoryItem,
} from './schema';
import bcrypt from 'bcryptjs';

// ─── Helpers ────────────────────────────────────────────────────────────────
const DAY = 24 * 60 * 60 * 1000;
const now = Date.now();
/** Offset in days from today (negative = past), at a given hour. */
const at = (days: number, hour: number): Date => {
  const d = new Date(now + days * DAY);
  d.setHours(hour, 0, 0, 0);
  return d;
};

async function seed() {
  console.log('🌱 Seeding BeautyCore database...\n');

  // ─── Clear existing data (children first, FK order) ───────────────────────
  console.log('  Clearing existing data...');
  await db.delete(aiGenerations);
  await db.delete(appointments);
  await db.delete(clientProfiles);
  await db.delete(inventory);
  await db.delete(users);

  // ─── Users ───────────────────────────────────────────────────────────────
  console.log('  Creating users...');
  const hash = (pw: string) => bcrypt.hashSync(pw, 10);

  const seedUsers: NewUser[] = [
    // Demo accounts (documented in the walkthrough)
    { email: 'admin@andreas.com',   name: 'Andrea Santos',    passwordHash: hash('admin123'),   role: 'admin'   },
    { email: 'lara@andreas.com',    name: 'Lara Villanueva',  passwordHash: hash('stylist123'), role: 'stylist' },
    { email: 'maria@email.com',     name: 'Maria Cruz',       passwordHash: hash('client123'),  role: 'client'  },
    // Supporting cast, for realistic tables
    { email: 'joy@andreas.com',     name: 'Joy Ramirez',      passwordHash: hash('stylist123'), role: 'stylist' },
    { email: 'bea@andreas.com',     name: 'Bea Mendoza',      passwordHash: hash('stylist123'), role: 'stylist' },
    { email: 'sofia@email.com',     name: 'Sofia Reyes',      passwordHash: hash('client123'),  role: 'client'  },
    { email: 'trisha@email.com',    name: 'Trisha Lim',       passwordHash: hash('client123'),  role: 'client'  },
    { email: 'kim@email.com',       name: 'Kim Dela Cruz',    passwordHash: hash('client123'),  role: 'client'  },
    { email: 'nica@email.com',      name: 'Nica Bautista',    passwordHash: hash('client123'),  role: 'client'  },
  ];

  const insertedUsers = await db.insert(users).values(seedUsers).returning();
  const byEmail = (e: string) => {
    const u = insertedUsers.find((x) => x.email === e);
    if (!u) throw new Error(`Seed error: user ${e} not found after insert`);
    return u;
  };

  const admin  = byEmail('admin@andreas.com');
  const lara   = byEmail('lara@andreas.com');
  const joy    = byEmail('joy@andreas.com');
  const bea    = byEmail('bea@andreas.com');
  const maria  = byEmail('maria@email.com');
  const sofia  = byEmail('sofia@email.com');
  const trisha = byEmail('trisha@email.com');
  const kim    = byEmail('kim@email.com');
  const nica   = byEmail('nica@email.com');

  console.log(`    ✓ ${insertedUsers.length} users`);

  // ─── Client Profiles ─────────────────────────────────────────────────────
  console.log('  Creating client profiles...');
  await db.insert(clientProfiles).values([
    {
      userId: maria.id,
      hairPreferences: 'Prefers warm balayage tones, avoids heavy bleach. Shoulder-length layers.',
      nailPreferences: 'Almond shape, muted pastels, minimal art. Sensitive to strong acetone.',
      styleHistory: [
        { date: '2026-05-14', type: 'hair', description: 'Caramel balayage with soft layers' },
        { date: '2026-06-28', type: 'nail', description: 'Almond gel, dusty rose' },
      ],
    },
    {
      userId: sofia.id,
      hairPreferences: 'Loves bold colour — has done burgundy and copper. Open to short cuts.',
      nailPreferences: 'Coffin shape, chrome finishes, statement art.',
      styleHistory: [{ date: '2026-07-02', type: 'nail', description: 'Coffin chrome, emerald' }],
    },
    {
      userId: trisha.id,
      hairPreferences: 'Keratin treatments, low-maintenance straight styles.',
      nailPreferences: 'Short square, French tips, clear topcoat.',
      styleHistory: [],
    },
    {
      userId: kim.id,
      hairPreferences: 'Curly hair — needs hydration-focused treatments, no heat styling.',
      nailPreferences: 'Round natural, nude tones.',
      styleHistory: [],
    },
    {
      userId: nica.id,
      hairPreferences: 'Growing out a pixie cut. Interested in face-framing highlights.',
      nailPreferences: 'Stiletto, dark jewel tones, ombré.',
      styleHistory: [],
    },
  ]);
  console.log('    ✓ 5 client profiles');

  // ─── Appointments ────────────────────────────────────────────────────────
  console.log('  Creating appointments...');
  const seedAppointments: NewAppointment[] = [
    // Upcoming
    { clientId: maria.id,  stylistId: lara.id, serviceName: 'Balayage & Gloss',        serviceType: 'hair',      appointmentDate: at(2, 10),  status: 'confirmed', totalPrice: 3500, notes: 'Warm caramel tones, no bleach on roots.' },
    { clientId: sofia.id,  stylistId: joy.id,  serviceName: 'Chrome Gel Extensions',   serviceType: 'nail',      appointmentDate: at(1, 14),  status: 'confirmed', totalPrice: 1800, notes: 'Coffin shape, emerald chrome.' },
    { clientId: trisha.id, stylistId: bea.id,  serviceName: 'Keratin Smoothing',       serviceType: 'treatment', appointmentDate: at(4, 11),  status: 'pending',   totalPrice: 4200, notes: null },
    { clientId: kim.id,    stylistId: lara.id, serviceName: 'Hydration Treatment',     serviceType: 'treatment', appointmentDate: at(5, 15),  status: 'pending',   totalPrice: 2200, notes: 'Curly hair — no heat.' },
    { clientId: nica.id,   stylistId: joy.id,  serviceName: 'Stiletto Ombré Set',      serviceType: 'nail',      appointmentDate: at(3, 13),  status: 'confirmed', totalPrice: 2000, notes: 'Deep sapphire ombré.' },
    { clientId: maria.id,  stylistId: joy.id,  serviceName: 'Almond Gel Manicure',     serviceType: 'nail',      appointmentDate: at(7, 16),  status: 'pending',   totalPrice: 1200, notes: null },
    // Past — completed
    { clientId: maria.id,  stylistId: joy.id,  serviceName: 'Almond Gel Manicure',     serviceType: 'nail',      appointmentDate: at(-9, 16),  status: 'completed', totalPrice: 1200, notes: 'Dusty rose.' },
    { clientId: sofia.id,  stylistId: bea.id,  serviceName: 'Full Colour — Burgundy',  serviceType: 'hair',      appointmentDate: at(-14, 10), status: 'completed', totalPrice: 3800, notes: null },
    { clientId: trisha.id, stylistId: joy.id,  serviceName: 'French Tip Manicure',     serviceType: 'nail',      appointmentDate: at(-6, 12),  status: 'completed', totalPrice: 900,  notes: null },
    { clientId: kim.id,    stylistId: lara.id, serviceName: 'Deep Conditioning',       serviceType: 'treatment', appointmentDate: at(-21, 14), status: 'completed', totalPrice: 1500, notes: null },
    { clientId: nica.id,   stylistId: bea.id,  serviceName: 'Pixie Trim & Style',      serviceType: 'hair',      appointmentDate: at(-30, 9),  status: 'completed', totalPrice: 1100, notes: null },
    { clientId: sofia.id,  stylistId: joy.id,  serviceName: 'Coffin Chrome Set',       serviceType: 'nail',      appointmentDate: at(-35, 13), status: 'completed', totalPrice: 1800, notes: null },
    // Cancelled
    { clientId: trisha.id, stylistId: lara.id, serviceName: 'Root Touch-Up',           serviceType: 'hair',      appointmentDate: at(-3, 11),  status: 'cancelled', totalPrice: 1600, notes: 'Client rescheduled.' },
    { clientId: kim.id,    stylistId: bea.id,  serviceName: 'Nail Art Session',        serviceType: 'nail',      appointmentDate: at(-1, 15),  status: 'cancelled', totalPrice: 1400, notes: null },
  ];

  await db.insert(appointments).values(seedAppointments);
  console.log(`    ✓ ${seedAppointments.length} appointments`);

  // ─── Inventory ───────────────────────────────────────────────────────────
  console.log('  Creating inventory...');
  const seedInventory: NewInventoryItem[] = [
    { productName: 'Developer 20 Vol (1L)',        category: 'Hair Colour',  currentStock: 24, minimumThreshold: 10, unitPrice: 450,  status: 'in_stock',     lastRestocked: at(-12, 9) },
    { productName: 'Bleach Powder (500g)',         category: 'Hair Colour',  currentStock: 8,  minimumThreshold: 10, unitPrice: 780,  status: 'low_stock',    lastRestocked: at(-20, 9) },
    { productName: 'Toner — Ash Blonde',           category: 'Hair Colour',  currentStock: 15, minimumThreshold: 8,  unitPrice: 620,  status: 'in_stock',     lastRestocked: at(-8, 9)  },
    { productName: 'Permanent Colour — Burgundy',  category: 'Hair Colour',  currentStock: 3,  minimumThreshold: 6,  unitPrice: 540,  status: 'low_stock',    lastRestocked: at(-28, 9) },
    { productName: 'Keratin Treatment Kit',        category: 'Treatment',    currentStock: 0,  minimumThreshold: 4,  unitPrice: 2400, status: 'out_of_stock', lastRestocked: at(-45, 9) },
    { productName: 'Argan Oil Serum (100ml)',      category: 'Treatment',    currentStock: 32, minimumThreshold: 12, unitPrice: 890,  status: 'in_stock',     lastRestocked: at(-5, 9)  },
    { productName: 'Deep Conditioning Masque',     category: 'Treatment',    currentStock: 18, minimumThreshold: 10, unitPrice: 1100, status: 'in_stock',     lastRestocked: at(-10, 9) },
    { productName: 'Gel Polish — Dusty Rose',      category: 'Nail',         currentStock: 12, minimumThreshold: 6,  unitPrice: 380,  status: 'in_stock',     lastRestocked: at(-7, 9)  },
    { productName: 'Gel Polish — Emerald Chrome',  category: 'Nail',         currentStock: 4,  minimumThreshold: 6,  unitPrice: 420,  status: 'low_stock',    lastRestocked: at(-18, 9) },
    { productName: 'Gel Polish — Clear Topcoat',   category: 'Nail',         currentStock: 27, minimumThreshold: 10, unitPrice: 350,  status: 'in_stock',     lastRestocked: at(-4, 9)  },
    { productName: 'Acrylic Powder (Clear, 250g)', category: 'Nail',         currentStock: 9,  minimumThreshold: 5,  unitPrice: 950,  status: 'in_stock',     lastRestocked: at(-15, 9) },
    { productName: 'Nail Tips — Coffin (500pc)',   category: 'Nail',         currentStock: 2,  minimumThreshold: 5,  unitPrice: 640,  status: 'low_stock',    lastRestocked: at(-33, 9) },
    { productName: 'Nail Tips — Almond (500pc)',   category: 'Nail',         currentStock: 14, minimumThreshold: 5,  unitPrice: 640,  status: 'in_stock',     lastRestocked: at(-11, 9) },
    { productName: 'Cuticle Oil (50ml)',           category: 'Nail',         currentStock: 21, minimumThreshold: 8,  unitPrice: 290,  status: 'in_stock',     lastRestocked: at(-6, 9)  },
    { productName: 'Acetone Remover (1L)',         category: 'Nail',         currentStock: 0,  minimumThreshold: 4,  unitPrice: 320,  status: 'out_of_stock', lastRestocked: at(-40, 9) },
    { productName: 'Disposable Towels (200pc)',    category: 'Supplies',     currentStock: 45, minimumThreshold: 20, unitPrice: 480,  status: 'in_stock',     lastRestocked: at(-9, 9)  },
    { productName: 'Nitrile Gloves (100pc)',       category: 'Supplies',     currentStock: 7,  minimumThreshold: 15, unitPrice: 350,  status: 'low_stock',    lastRestocked: at(-22, 9) },
    { productName: 'Sanitising Solution (5L)',     category: 'Supplies',     currentStock: 11, minimumThreshold: 6,  unitPrice: 720,  status: 'in_stock',     lastRestocked: at(-13, 9) },
  ];

  await db.insert(inventory).values(seedInventory);
  console.log(`    ✓ ${seedInventory.length} inventory items`);

  // ─── AI Generations ──────────────────────────────────────────────────────
  // Analysis is real (Gemini vision); preview generation is stubbed pending a
  // provider, so generatedImageUrl is null on these records.
  console.log('  Creating AI generation records...');
  await db.insert(aiGenerations).values([
    {
      clientId: maria.id,
      sourceImageUrl: '/demo/nails-before-01.jpg',
      promptText: 'Almond-shape nails with a soft dusty-rose gel finish, subtle pearl accent on the ring finger',
      generatedImageUrl: null,
      styleType: 'nail',
      analysisResult: {
        category: 'nails',
        currentAttributes: { shapeOrCut: 'Short square', color: 'Bare / unpolished', condition: 'Healthy, slight dryness at cuticle' },
        recommendations: [
          { title: 'Soft Rose Almond',     colorPalette: 'Dusty rose, pearl white',     designDetails: 'Almond shape, glossy gel, single pearl accent nail', reasoning: 'Almond elongates shorter nail beds; muted rose suits your warm undertone.', generationPrompt: 'Almond-shape nails, dusty rose gel polish, pearl accent, salon macro photo' },
          { title: 'Milky Glazed',         colorPalette: 'Milky white, iridescent',     designDetails: 'Sheer milky base with a chrome glaze topcoat',       reasoning: 'Low-maintenance grow-out; hides regrowth line as nails extend.',       generationPrompt: 'Milky white glazed nails, iridescent chrome finish, macro photo' },
          { title: 'Warm Nude French',     colorPalette: 'Warm nude, cream tip',        designDetails: 'Micro-French tip in cream over a warm nude base',    reasoning: 'A modern take on French that flatters your skin tone.',                generationPrompt: 'Warm nude nails with thin cream French tips, elegant macro photo' },
        ],
      },
      createdAt: at(-9, 15),
    },
    {
      clientId: sofia.id,
      sourceImageUrl: '/demo/nails-before-02.jpg',
      promptText: 'Coffin-shape nails, emerald chrome finish with gold foil accents',
      generatedImageUrl: null,
      styleType: 'nail',
      analysisResult: {
        category: 'nails',
        currentAttributes: { shapeOrCut: 'Coffin, medium length', color: 'Dark green chrome', condition: 'Gel intact, minor lifting at edges' },
        recommendations: [
          { title: 'Emerald Chrome',       colorPalette: 'Emerald, gold',               designDetails: 'Full chrome coverage with gold foil flecks',        reasoning: 'Builds on your existing bold palette with added dimension.',           generationPrompt: 'Coffin nails, emerald chrome with gold foil, editorial macro photo' },
          { title: 'Midnight Jewel',       colorPalette: 'Sapphire, black',             designDetails: 'Deep sapphire base, black marble veining',          reasoning: 'Jewel tones you already favour, in a moodier direction.',              generationPrompt: 'Coffin nails, sapphire with black marble veining, macro photo' },
          { title: 'Copper Mirror',        colorPalette: 'Copper, bronze',              designDetails: 'Mirror-chrome copper, high shine',                  reasoning: 'Warm metallic contrast to the cool tones in your history.',            generationPrompt: 'Coffin nails, copper mirror chrome finish, macro photo' },
        ],
      },
      createdAt: at(-4, 11),
    },
    {
      clientId: maria.id,
      sourceImageUrl: '/demo/hair-before-01.jpg',
      promptText: 'Shoulder-length caramel balayage with soft face-framing layers',
      generatedImageUrl: null,
      styleType: 'hair',
      analysisResult: {
        category: 'hair',
        currentAttributes: { shapeOrCut: 'Shoulder-length, blunt', color: 'Natural dark brown', condition: 'Healthy, minimal damage' },
        recommendations: [
          { title: 'Caramel Balayage',     colorPalette: 'Caramel, honey',              designDetails: 'Hand-painted balayage from mid-length, soft layers',  reasoning: 'Warm tones complement your complexion; low regrowth upkeep.',        generationPrompt: 'Shoulder-length caramel balayage, soft layers, salon portrait' },
          { title: 'Golden Money Piece',   colorPalette: 'Golden blonde, dark base',    designDetails: 'Face-framing golden highlights over natural base',     reasoning: 'Brightens the face with minimal overall commitment.',                 generationPrompt: 'Dark brown hair with golden face-framing highlights, salon portrait' },
          { title: 'Chocolate Gloss',      colorPalette: 'Rich chocolate, subtle red',  designDetails: 'All-over gloss with warm red undertone, blunt cut',    reasoning: 'Adds shine and depth without lifting your natural colour.',           generationPrompt: 'Rich chocolate brown glossy hair, blunt shoulder cut, salon portrait' },
        ],
      },
      createdAt: at(-16, 14),
    },
    {
      clientId: nica.id,
      sourceImageUrl: '/demo/hair-before-02.jpg',
      promptText: 'Grown-out pixie with face-framing highlights and textured styling',
      generatedImageUrl: null,
      styleType: 'hair',
      analysisResult: {
        category: 'hair',
        currentAttributes: { shapeOrCut: 'Grown-out pixie, ear length', color: 'Natural black', condition: 'Healthy, uneven grow-out at nape' },
        recommendations: [
          { title: 'Textured Shag',        colorPalette: 'Natural black',               designDetails: 'Choppy layers to bridge the grow-out, piecey texture', reasoning: 'Turns the awkward grow-out phase into an intentional shape.',        generationPrompt: 'Textured shag haircut, ear length, natural black, salon portrait' },
          { title: 'Ash Money Piece',      colorPalette: 'Ash brown, black',            designDetails: 'Two face-framing ash panels over natural black',       reasoning: 'Adds contrast and draws the eye up while length evens out.',          generationPrompt: 'Short black hair with ash brown face-framing panels, salon portrait' },
          { title: 'Soft Bixie',           colorPalette: 'Natural black',               designDetails: 'Bob-pixie hybrid with rounded silhouette',            reasoning: 'A structured next step that keeps most of your current length.',      generationPrompt: 'Soft bixie haircut, rounded silhouette, black hair, salon portrait' },
        ],
      },
      createdAt: at(-2, 10),
    },
    {
      clientId: trisha.id,
      sourceImageUrl: '/demo/nails-before-03.jpg',
      promptText: 'Short square nails with a clean micro-French tip',
      generatedImageUrl: null,
      styleType: 'nail',
      analysisResult: {
        category: 'nails',
        currentAttributes: { shapeOrCut: 'Short square', color: 'Clear topcoat', condition: 'Strong, well-maintained' },
        recommendations: [
          { title: 'Micro French',         colorPalette: 'Sheer pink, white',           designDetails: 'Ultra-thin white tip on a sheer pink base',           reasoning: 'Matches your minimal preference with a cleaner modern line.',        generationPrompt: 'Short square nails, micro French tip, sheer pink base, macro photo' },
          { title: 'Clean Girl Nude',      colorPalette: 'Warm nude',                   designDetails: 'Single-tone warm nude, high-gloss finish',            reasoning: 'The lowest-maintenance option; grows out invisibly.',                 generationPrompt: 'Short square nude nails, high gloss, macro photo' },
          { title: 'Subtle Chrome',        colorPalette: 'Pearl, soft pink',            designDetails: 'Pearl chrome dusted over a soft pink base',           reasoning: 'Adds interest while staying within your understated palette.',        generationPrompt: 'Short square nails, pearl chrome over soft pink, macro photo' },
        ],
      },
      createdAt: at(-6, 13),
    },
  ]);
  console.log('    ✓ 5 AI generation records');

  // ─── Summary ─────────────────────────────────────────────────────────────
  console.log('\n✅ Seed complete!\n');
  console.log('   Demo accounts:');
  console.log('   ┌─────────────────────┬──────────────┬─────────┐');
  console.log('   │ admin@andreas.com   │ admin123     │ admin   │');
  console.log('   │ lara@andreas.com    │ stylist123   │ stylist │');
  console.log('   │ maria@email.com     │ client123    │ client  │');
  console.log('   └─────────────────────┴──────────────┴─────────┘\n');
}

seed()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error('\n❌ Seed failed:', err);
    process.exit(1);
  });
