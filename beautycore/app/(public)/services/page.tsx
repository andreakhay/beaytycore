'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { serviceGroups } from '@/lib/services';

export default function ServicesPage() {
  const [active, setActive] = useState(serviceGroups[0].id);
  const group = serviceGroups.find((g) => g.id === active) ?? serviceGroups[0];

  return (
    <>
      {/* Header */}
      <section className="relative overflow-hidden border-b border-purple-light/15 px-6 py-20 lg:px-10">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-20 -top-20 h-96 w-96 rounded-full bg-purple/20 blur-[110px]"
        />
        <div className="relative mx-auto max-w-7xl">
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-[3px] text-gold">
            Our Services
          </p>
          <h1 className="mb-4 font-serif text-5xl text-white sm:text-6xl">
            The full menu
          </h1>
          <p className="max-w-xl text-[15px] leading-relaxed text-secondary">
            Every service is delivered by a certified specialist. Prices are in
            Philippine pesos — some vary with length, thickness, or condition,
            so those are marked <span className="text-gold">Mula</span> (from).
          </p>
        </div>
      </section>

      {/* Tabs */}
      <section className="sticky top-[73px] z-30 border-b border-purple-light/15 bg-deep/85 backdrop-blur-md">
        <div className="scrollbar-thin mx-auto flex max-w-7xl gap-1 overflow-x-auto px-6 lg:px-10">
          {serviceGroups.map((g) => (
            <button
              key={g.id}
              onClick={() => setActive(g.id)}
              className={`relative whitespace-nowrap px-4 py-4 text-[11px] font-medium uppercase tracking-[1.5px] transition-colors ${
                active === g.id ? 'text-gold' : 'text-muted hover:text-secondary'
              }`}
            >
              {g.label}
              {active === g.id && (
                <motion.span
                  layoutId="service-tab"
                  className="absolute bottom-0 left-0 h-px w-full bg-gold"
                />
              )}
            </button>
          ))}
        </div>
      </section>

      {/* Panel */}
      <section className="px-6 py-16 lg:px-10">
        <div className="mx-auto max-w-7xl">
          <AnimatePresence mode="wait">
            <motion.div
              key={group.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.3 }}
            >
              <div className="mb-10 max-w-2xl">
                <h2 className="mb-2 font-serif text-3xl text-white">{group.label}</h2>
                <p className="mb-4 text-[11px] uppercase tracking-[2px] text-gold">
                  {group.sub}
                </p>
                <p className="text-[14px] leading-relaxed text-secondary">{group.intro}</p>
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                {group.categories.map((cat) => (
                  <div
                    key={cat.title}
                    className="rounded-sm border border-purple-light/15 bg-card p-6"
                  >
                    <h3 className="mb-5 border-b border-purple-light/15 pb-3 text-[11px] font-semibold uppercase tracking-[2.5px] text-gold">
                      {cat.title}
                    </h3>
                    <ul className="flex flex-col gap-3">
                      {cat.items.map((s) => (
                        <li
                          key={s.name}
                          className="flex items-baseline justify-between gap-4 border-b border-white/[0.04] pb-3 last:border-0 last:pb-0"
                        >
                          <span className="text-[13px] text-secondary">{s.name}</span>
                          <span className="shrink-0 text-[13px] font-medium text-white">
                            {s.price}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>

              <div className="mt-10 flex flex-wrap gap-3">
                <Link
                  href={`/booking?service=${group.id}`}
                  className="group flex items-center gap-2 bg-gold px-7 py-3.5 text-[11px] font-semibold uppercase tracking-[2px] text-card transition-all hover:bg-gold-hover"
                >
                  Book {group.label}
                  <ArrowRight size={14} className="transition-transform group-hover:translate-x-1" />
                </Link>
                <Link
                  href="/contact"
                  className="border border-purple-light/40 px-7 py-3.5 text-[11px] font-semibold uppercase tracking-[2px] text-secondary transition-all hover:border-purple-light hover:text-white"
                >
                  Ask a Question
                </Link>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </section>
    </>
  );
}
