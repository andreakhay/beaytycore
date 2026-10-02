'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Hand, Scissors, Sparkles, Flame } from 'lucide-react';
import { PageHeader, Card, Skeleton, EmptyState } from '@/components/ui';

interface ServiceRow {
  serviceName: string;
  serviceType: string;
  bookings: number;
  revenue: number;
}

interface GenerationRow {
  styleType: 'hair' | 'nail';
  analysisResult: {
    recommendations?: Array<{ title: string }>;
  } | null;
}

const typeIcon: Record<string, typeof Hand> = {
  nail: Hand,
  hair: Scissors,
  treatment: Sparkles,
  massage: Sparkles,
  aesthetic: Sparkles,
};

export default function AdminMarketTrendsPage() {
  const [services, setServices] = useState<ServiceRow[]>([]);
  const [generations, setGenerations] = useState<GenerationRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/admin/stats').then((r) => r.json()),
      fetch('/api/generations').then((r) => r.json()),
    ])
      .then(([s, g]) => {
        setServices(s.topServices ?? []);
        setGenerations(g.generations ?? []);
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  const maxBookings = Math.max(...services.map((s) => s.bookings), 1);

  // Which service types are actually being booked.
  const byType = services.reduce<Record<string, number>>((acc, s) => {
    acc[s.serviceType] = (acc[s.serviceType] ?? 0) + s.bookings;
    return acc;
  }, {});
  const totalByType = Object.values(byType).reduce((a, b) => a + b, 0);

  // What the AI is recommending most — a genuine demand signal.
  const aiTitles = generations
    .flatMap((g) => g.analysisResult?.recommendations?.map((r) => r.title) ?? [])
    .reduce<Record<string, number>>((acc, t) => {
      acc[t] = (acc[t] ?? 0) + 1;
      return acc;
    }, {});
  const topAiStyles = Object.entries(aiTitles)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  return (
    <>
      <PageHeader
        title="Market Trends"
        subtitle="What clients are booking, and what the AI advisor is recommending."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Most booked */}
        <Card>
          <h2 className="mb-5 flex items-center gap-2 font-serif text-xl text-white">
            <Flame size={17} className="text-gold" />
            Most Booked Services
          </h2>

          {loading ? (
            <div className="flex flex-col gap-3">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : services.length === 0 ? (
            <EmptyState icon={TrendingUp} title="No booking data yet" />
          ) : (
            <ul className="flex flex-col gap-4">
              {services.map((s, i) => {
                const Icon = typeIcon[s.serviceType] ?? Sparkles;
                return (
                  <li key={`${s.serviceName}-${i}`}>
                    <div className="mb-1.5 flex items-center justify-between gap-3">
                      <span className="flex min-w-0 items-center gap-2">
                        <Icon size={13} className="shrink-0 text-purple-glow" />
                        <span className="truncate text-[12px] text-secondary">
                          {s.serviceName}
                        </span>
                      </span>
                      <span className="shrink-0 text-[12px] font-medium text-white">
                        {s.bookings}
                      </span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-surface/60">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(s.bookings / maxBookings) * 100}%` }}
                        transition={{ duration: 0.7, delay: i * 0.06, ease: 'easeOut' }}
                        className="h-full rounded-full bg-gradient-to-r from-purple-light to-gold"
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        {/* Category split */}
        <Card>
          <h2 className="mb-5 font-serif text-xl text-white">Demand by Category</h2>

          {loading ? (
            <Skeleton className="h-48 w-full" />
          ) : totalByType === 0 ? (
            <EmptyState icon={TrendingUp} title="No data yet" />
          ) : (
            <ul className="flex flex-col gap-4">
              {Object.entries(byType)
                .sort((a, b) => b[1] - a[1])
                .map(([type, count], i) => {
                  const Icon = typeIcon[type] ?? Sparkles;
                  const pct = Math.round((count / totalByType) * 100);
                  return (
                    <li key={type}>
                      <div className="mb-1.5 flex items-center justify-between">
                        <span className="flex items-center gap-2 text-[12px] capitalize text-secondary">
                          <Icon size={13} className="text-purple-glow" />
                          {type}
                        </span>
                        <span className="text-[12px] text-white">
                          {count}
                          <span className="ml-1.5 text-[11px] text-muted">({pct}%)</span>
                        </span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-surface/60">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ duration: 0.7, delay: i * 0.08, ease: 'easeOut' }}
                          className="h-full rounded-full bg-purple"
                        />
                      </div>
                    </li>
                  );
                })}
            </ul>
          )}
        </Card>

        {/* AI recommendation trends */}
        <Card className="lg:col-span-2">
          <h2 className="mb-2 flex items-center gap-2 font-serif text-xl text-white">
            <Sparkles size={17} className="text-gold" />
            AI Advisor Trends
          </h2>
          <p className="mb-5 text-[12px] text-muted">
            Styles the AI has recommended most across client photo analyses — an
            early signal of what to stock and train for.
          </p>

          {loading ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : topAiStyles.length === 0 ? (
            <EmptyState
              icon={Sparkles}
              title="No AI analyses yet"
              body="Once clients use the AI Advisor, recommendation trends appear here."
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {topAiStyles.map(([title, count], i) => (
                <motion.div
                  key={title}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.05 }}
                  className="flex items-center justify-between gap-3 rounded-sm border border-purple-light/15 bg-surface/25 p-3.5"
                >
                  <span className="min-w-0 truncate text-[12px] text-secondary">
                    {title}
                  </span>
                  <span className="shrink-0 rounded-full border border-gold/30 bg-gold/10 px-2 py-0.5 text-[10px] font-medium text-gold">
                    {count}×
                  </span>
                </motion.div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
