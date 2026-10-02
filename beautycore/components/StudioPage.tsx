'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight } from 'lucide-react';
import { PageHeader, Card, formatPeso } from '@/components/ui';

/** Shape of one option column in the builder. */
export interface BuilderOption {
  id: string;
  label: string;
  /** Added to the base price. */
  price: number;
  /** Optional swatch colour for colour pickers. */
  swatch?: string;
}

export interface BuilderGroup {
  key: string;
  label: string;
  options: BuilderOption[];
}

export interface PresetDesign {
  id: string;
  name: string;
  description: string;
  tags: string[];
  price: number;
  gradient: string;
}

interface StudioProps {
  title: string;
  subtitle: string;
  bookingHref: string;
  basePrice: number;
  presets: PresetDesign[];
  builder: BuilderGroup[];
}

/**
 * Shared studio page — a preset catalogue plus a configurator that prices
 * itself live. Used by both the nail and hair studios.
 */
export default function StudioPage({
  title,
  subtitle,
  bookingHref,
  basePrice,
  presets,
  builder,
}: StudioProps) {
  const [tab, setTab] = useState<'browse' | 'build'>('browse');

  // Default each group to its first option.
  const [choice, setChoice] = useState<Record<string, string>>(() =>
    Object.fromEntries(builder.map((g) => [g.key, g.options[0].id]))
  );

  const selected = useMemo(
    () =>
      builder.map((g) => ({
        group: g,
        option: g.options.find((o) => o.id === choice[g.key]) ?? g.options[0],
      })),
    [builder, choice]
  );

  const total = useMemo(
    () => basePrice + selected.reduce((sum, s) => sum + s.option.price, 0),
    [basePrice, selected]
  );

  const summary = selected.map((s) => s.option.label).join(' · ');

  return (
    <>
      <PageHeader title={title} subtitle={subtitle} />

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-sm border border-purple-light/15 bg-surface/30 p-1">
        {(
          [
            { key: 'browse', label: 'Browse Designs' },
            { key: 'build', label: 'Build Your Own' },
          ] as const
        ).map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`relative flex-1 rounded-sm py-2.5 text-[11px] font-medium uppercase tracking-[1.5px] transition-colors ${
              tab === t.key ? 'text-white' : 'text-muted hover:text-secondary'
            }`}
          >
            {tab === t.key && (
              <motion.span
                layoutId="studio-tab"
                className="absolute inset-0 rounded-sm bg-purple/30"
              />
            )}
            <span className="relative">{t.label}</span>
          </button>
        ))}
      </div>

      {/* ─── Browse ──────────────────────────────────────────────────── */}
      {tab === 'browse' && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {presets.map((p, i) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: Math.min(i * 0.05, 0.3) }}
            >
              <div className="group flex h-full flex-col overflow-hidden rounded-sm border border-purple-light/15 bg-card transition-colors hover:border-gold/40">
                <div
                  className="h-32 w-full transition-transform duration-500 group-hover:scale-105"
                  style={{ background: p.gradient }}
                />
                <div className="flex flex-1 flex-col p-5">
                  <h3 className="mb-1.5 font-serif text-lg text-white">{p.name}</h3>
                  <p className="mb-3 flex-1 text-[12px] leading-relaxed text-muted">
                    {p.description}
                  </p>
                  <div className="mb-4 flex flex-wrap gap-1.5">
                    {p.tags.map((t) => (
                      <span
                        key={t}
                        className="rounded-full border border-purple-light/20 px-2 py-0.5 text-[10px] text-muted"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[15px] font-medium text-white">
                      {formatPeso(p.price)}
                    </span>
                    <Link
                      href={bookingHref}
                      className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[1.5px] text-gold hover:underline"
                    >
                      Book
                      <ArrowRight size={11} />
                    </Link>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* ─── Build ───────────────────────────────────────────────────── */}
      {tab === 'build' && (
        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <div className="flex flex-col gap-4">
            {builder.map((g) => (
              <Card key={g.key}>
                <h3 className="mb-4 text-[10px] font-semibold uppercase tracking-[2px] text-gold">
                  {g.label}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {g.options.map((o) => {
                    const active = choice[g.key] === o.id;
                    return (
                      <button
                        key={o.id}
                        onClick={() => setChoice((c) => ({ ...c, [g.key]: o.id }))}
                        className={`flex items-center gap-2 rounded-sm border px-3.5 py-2 text-[12px] transition-colors ${
                          active
                            ? 'border-gold/50 bg-gold/10 text-white'
                            : 'border-purple-light/15 text-muted hover:border-purple-light/40'
                        }`}
                      >
                        {o.swatch && (
                          <span
                            aria-hidden
                            className="h-3.5 w-3.5 rounded-full border border-white/20"
                            style={{ background: o.swatch }}
                          />
                        )}
                        {o.label}
                        {o.price > 0 && (
                          <span className="text-[10px] text-muted">
                            +{formatPeso(o.price)}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </Card>
            ))}
          </div>

          {/* Live summary */}
          <div className="lg:sticky lg:top-8 lg:self-start">
            <Card>
              <h3 className="mb-4 text-[10px] font-semibold uppercase tracking-[2px] text-gold">
                Your Design
              </h3>

              <div
                aria-hidden
                className="mb-5 h-28 rounded-sm border border-purple-light/20"
                style={{
                  background: `linear-gradient(135deg, ${
                    selected.find((s) => s.option.swatch)?.option.swatch ?? '#7b2fa0'
                  }, #1a0a2e)`,
                }}
              />

              <dl className="mb-5 flex flex-col gap-2.5">
                {selected.map((s) => (
                  <div key={s.group.key} className="flex justify-between gap-3">
                    <dt className="text-[11px] text-muted">{s.group.label}</dt>
                    <dd className="text-right text-[12px] text-secondary">
                      {s.option.label}
                    </dd>
                  </div>
                ))}
              </dl>

              <div className="mb-5 flex items-baseline justify-between border-t border-purple-light/15 pt-4">
                <span className="text-[11px] uppercase tracking-wide text-muted">
                  Estimated
                </span>
                <span className="font-serif text-2xl text-white">
                  {formatPeso(total)}
                </span>
              </div>

              <Link
                href={`${bookingHref}&notes=${encodeURIComponent(summary)}`}
                className="mb-2.5 flex w-full items-center justify-center gap-2 bg-gold px-5 py-3 text-[11px] font-semibold uppercase tracking-[2px] text-card transition-colors hover:bg-gold-hover"
              >
                Book This Design
              </Link>
              <Link
                href="/client/ai-advisor"
                className="flex w-full items-center justify-center gap-2 border border-purple-light/40 px-5 py-2.5 text-[10px] font-semibold uppercase tracking-[1.5px] text-secondary transition-colors hover:border-gold/50 hover:text-gold"
              >
                <Sparkles size={12} />
                Ask the AI Advisor
              </Link>

              <p className="mt-4 text-[11px] leading-relaxed text-muted">
                Final pricing is confirmed in-salon and can vary with length,
                thickness, and condition.
              </p>
            </Card>
          </div>
        </div>
      )}
    </>
  );
}
