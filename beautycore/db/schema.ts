import { pgTable, uuid, text, timestamp, varchar, integer, jsonb, pgEnum } from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';

// ─── Enums ──────────────────────────────────────────────────────────────────
export const userRoleEnum = pgEnum('user_role', ['admin', 'stylist', 'client']);
export const appointmentStatusEnum = pgEnum('appointment_status', ['pending', 'confirmed', 'completed', 'cancelled']);
export const productStatusEnum = pgEnum('product_status', ['in_stock', 'low_stock', 'out_of_stock']);
export const styleTypeEnum = pgEnum('style_type', ['hair', 'nail']);

// ─── Users ──────────────────────────────────────────────────────────────────
export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: varchar('email', { length: 255 }).notNull().unique(),
  name: varchar('name', { length: 255 }).notNull(),
  passwordHash: text('password_hash').notNull(),
  role: userRoleEnum('role').notNull().default('client'),
  avatar: text('avatar'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// ─── Client Profiles ────────────────────────────────────────────────────────
export const clientProfiles = pgTable('client_profiles', {
  userId: uuid('user_id').primaryKey().references(() => users.id, { onDelete: 'cascade' }),
  hairPreferences: text('hair_preferences'),
  nailPreferences: text('nail_preferences'),
  styleHistory: jsonb('style_history').$type<Array<{
    date: string;
    type: 'hair' | 'nail';
    description: string;
  }>>(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// ─── Appointments ───────────────────────────────────────────────────────────
export const appointments = pgTable('appointments', {
  id: uuid('id').primaryKey().defaultRandom(),
  clientId: uuid('client_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
  stylistId: uuid('stylist_id').references(() => users.id, { onDelete: 'set null' }),
  serviceName: varchar('service_name', { length: 255 }).notNull(),
  serviceType: varchar('service_type', { length: 100 }).notNull(),
  appointmentDate: timestamp('appointment_date').notNull(),
  status: appointmentStatusEnum('status').notNull().default('pending'),
  totalPrice: integer('total_price'),
  notes: text('notes'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// ─── Inventory ──────────────────────────────────────────────────────────────
export const inventory = pgTable('inventory', {
  id: uuid('id').primaryKey().defaultRandom(),
  productName: varchar('product_name', { length: 255 }).notNull(),
  category: varchar('category', { length: 100 }).notNull(),
  currentStock: integer('current_stock').notNull().default(0),
  minimumThreshold: integer('minimum_threshold').notNull().default(10),
  unitPrice: integer('unit_price'),
  status: productStatusEnum('status').notNull().default('in_stock'),
  lastRestocked: timestamp('last_restocked'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// ─── AI Generations ─────────────────────────────────────────────────────────
export const aiGenerations = pgTable('ai_generations', {
  id: uuid('id').primaryKey().defaultRandom(),
  clientId: uuid('client_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
  sourceImageUrl: text('source_image_url').notNull(),
  promptText: text('prompt_text').notNull(),
  generatedImageUrl: text('generated_image_url'),
  styleType: styleTypeEnum('style_type').notNull(),
  analysisResult: jsonb('analysis_result').$type<{
    category: 'hair' | 'nails';
    currentAttributes: {
      shapeOrCut: string;
      color: string;
      condition: string;
    };
    recommendations: Array<{
      title: string;
      colorPalette: string;
      designDetails: string;
      reasoning: string;
      generationPrompt: string;
    }>;
  }>(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

// ─── Relations ──────────────────────────────────────────────────────────────
export const usersRelations = relations(users, ({ one, many }) => ({
  profile: one(clientProfiles, {
    fields: [users.id],
    references: [clientProfiles.userId],
  }),
  clientAppointments: many(appointments, { relationName: 'clientAppointments' }),
  stylistAppointments: many(appointments, { relationName: 'stylistAppointments' }),
  generations: many(aiGenerations),
}));

export const clientProfilesRelations = relations(clientProfiles, ({ one }) => ({
  user: one(users, {
    fields: [clientProfiles.userId],
    references: [users.id],
  }),
}));

export const appointmentsRelations = relations(appointments, ({ one }) => ({
  client: one(users, {
    fields: [appointments.clientId],
    references: [users.id],
    relationName: 'clientAppointments',
  }),
  stylist: one(users, {
    fields: [appointments.stylistId],
    references: [users.id],
    relationName: 'stylistAppointments',
  }),
}));

export const aiGenerationsRelations = relations(aiGenerations, ({ one }) => ({
  client: one(users, {
    fields: [aiGenerations.clientId],
    references: [users.id],
  }),
}));

// ─── Inferred Types ─────────────────────────────────────────────────────────
export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;
export type ClientProfile = typeof clientProfiles.$inferSelect;
export type NewClientProfile = typeof clientProfiles.$inferInsert;
export type Appointment = typeof appointments.$inferSelect;
export type NewAppointment = typeof appointments.$inferInsert;
export type InventoryItem = typeof inventory.$inferSelect;
export type NewInventoryItem = typeof inventory.$inferInsert;
export type AiGeneration = typeof aiGenerations.$inferSelect;
export type NewAiGeneration = typeof aiGenerations.$inferInsert;

export type UserRole = (typeof userRoleEnum.enumValues)[number];
export type AppointmentStatus = (typeof appointmentStatusEnum.enumValues)[number];
export type ProductStatus = (typeof productStatusEnum.enumValues)[number];
export type StyleType = (typeof styleTypeEnum.enumValues)[number];
