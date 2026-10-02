'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Package, AlertTriangle } from 'lucide-react';
import { PageHeader, Card } from '@/components/ui';
import { serviceGroups } from '@/lib/services';

export default function StylistServicesPage() {
  const [active, setActive] = useState(serviceGroups[0].id);
  const group = serviceGroups.find((g) => g.id === active) ?? serviceGroups[0];

  return (
    <>
      <PageHeader
        title="Service Menu"
        subtitle="Reference pricing for every service we offer."
      />

      {/* Category tabs */}
      <div className="scrollbar-thin mb-6 flex gap-1 overflow-x-auto rounded-sm border border-purple-light/15 bg-surface/30 p-1">
        {serviceGroups.map((g) => (
          <button
            key={g.id}
            onClick={() => setActive(g.id)}
            className={`relative whitespace-nowrap rounded-sm px-4 py-2.5 text-[11px] font-medium tracking-[1px] transition-colors ${
              active === g.id ? 'text-white' : 'text-muted hover:text-secondary'
            }`}
          >
            {active === g.id && (
              <motion.span
                layoutId="stylist-service-tab"
                className="absolute inset-0 rounded-sm bg-purple/30"
              />
            )}
            <span className="relative">{g.label}</span>
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={group.id}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.25 }}
        >
          <div className="mb-6">
            <h2 className="mb-1.5 font-serif text-2xl text-white">{group.label}</h2>
            <p className="mb-3 text-[11px] uppercase tracking-[2px] text-gold">
              {group.sub}
            </p>
            <p className="max-w-2xl text-[13px] leading-relaxed text-secondary">
              {group.intro}
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {group.categories.map((cat) => (
              <Card key={cat.title}>
                <h3 className="mb-5 flex items-center gap-2 border-b border-purple-light/15 pb-3 text-[11px] font-semibold uppercase tracking-[2.5px] text-gold">
                  <Package size={12} />
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
              </Card>
            ))}
          </div>

          <div className="mt-6 flex items-start gap-2.5 rounded-sm border border-info/20 bg-info/5 p-4 text-[12px] leading-relaxed text-info">
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            <span>
              Prices marked <strong>Mula</strong> (from) vary with length,
              thickness, and condition. Confirm the final quote with the client
              before starting, and note anything unusual on the appointment.
            </span>
          </div>
        </motion.div>
      </AnimatePresence>
    </>
  );
}
