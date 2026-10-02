'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Wallet, TrendingUp, CalendarCheck, Receipt } from 'lucide-react';
import { PageHeader, Card, Skeleton, EmptyState, formatPeso } from '@/components/ui';
import AnimatedCounter from '@/components/AnimatedCounter';
import type { AppointmentStatus } from '@/db/schema';

interface Stats {
  totalRevenue: number;
  monthRevenue: number;
  totalBookings: number;
}

interface StatusRow {
  status: AppointmentStatus;
  n: number;
}

interface ServiceRow {
  serviceName: string;
  serviceType: string;
  bookings: number;
  revenue: number;
}

const statusColor: Record<AppointmentStatus, string> = {
  completed: 'bg-info',
  confirmed: 'bg-success',
  pending: 'bg-warning',
  cancelled: 'bg-error',
};

export default function AdminFinancePage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [statusRows, setStatusRows] = useState<StatusRow[]>([]);
  const [services, setServices] = useState<ServiceRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/admin/stats')
      .then((r) => r.json())
      .then((d) => {
        setStats(d.stats ?? null);
        setStatusRows(d.statusBreakdown ?? []);
        setServices(d.topServices ?? []);
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  const completed = statusRows.find((s) => s.status === 'completed')?.n ?? 0;
  const avgTicket = completed > 0 ? Math.round((stats?.totalRevenue ?? 0) / completed) : 0;
  const totalStatuses = statusRows.reduce((sum, s) => sum + s.n, 0);
  const maxServiceRevenue = Math.max(...services.map((s) => s.revenue), 1);

  const cards = [
    {
      label: 'Total Revenue',
      value: stats?.totalRevenue ?? 0,
      prefix: '₱',
      icon: Wallet,
      note: 'From completed appointments',
      accent: 'text-gold',
    },
    {
      label: 'This Month',
      value: stats?.monthRevenue ?? 0,
      prefix: '₱',
      icon: TrendingUp,
      note: 'Month to date',
      accent: 'text-success',
    },
    {
      label: 'Completed',
      value: completed,
      icon: CalendarCheck,
      note: `of ${stats?.totalBookings ?? 0} bookings`,
      accent: 'text-info',
    },
    {
      label: 'Average Ticket',
      value: avgTicket,
      prefix: '₱',
      icon: Receipt,
      note: 'Per completed visit',
      accent: 'text-purple-glow',
    },
  ];

  return (
    <>
      <PageHeader
        title="Finance"
        subtitle="Revenue is counted from completed appointments only."
      />

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {loading
          ? [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-32 w-full" />)
          : cards.map((c, i) => (
              <motion.div
                key={c.label}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
              >
                <Card>
                  <div className="mb-3 flex items-start justify-between">
                    <span className="text-[10px] font-semibold uppercase tracking-[1.5px] text-muted">
                      {c.label}
                    </span>
                    <c.icon size={16} className={c.accent} />
                  </div>
                  <p className={`mb-1.5 font-serif text-3xl ${c.accent}`}>
                    <AnimatedCounter value={c.value} prefix={c.prefix} />
                  </p>
                  <p className="text-[11px] text-muted">{c.note}</p>
                </Card>
              </motion.div>
            ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Revenue by service */}
        <Card>
          <h2 className="mb-5 font-serif text-xl text-white">Revenue by Service</h2>
          {loading ? (
            <div className="flex flex-col gap-3">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : services.length === 0 ? (
            <EmptyState icon={Wallet} title="No revenue data yet" />
          ) : (
            <ul className="flex flex-col gap-4">
              {services.map((s, i) => (
                <li key={`${s.serviceName}-${i}`}>
                  <div className="mb-1.5 flex items-baseline justify-between gap-3">
                    <span className="truncate text-[12px] text-secondary">
                      {s.serviceName}
                    </span>
                    <span className="shrink-0 text-[12px] font-medium text-white">
                      {formatPeso(s.revenue)}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-surface/60">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(s.revenue / maxServiceRevenue) * 100}%` }}
                      transition={{ duration: 0.7, delay: i * 0.06, ease: 'easeOut' }}
                      className="h-full rounded-full bg-gradient-to-r from-purple to-gold"
                    />
                  </div>
                  <p className="mt-1 text-[10px] text-muted">
                    {s.bookings} booking{s.bookings !== 1 ? 's' : ''}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Booking status breakdown */}
        <Card>
          <h2 className="mb-5 font-serif text-xl text-white">Booking Status</h2>
          {loading ? (
            <Skeleton className="h-48 w-full" />
          ) : totalStatuses === 0 ? (
            <EmptyState icon={CalendarCheck} title="No bookings yet" />
          ) : (
            <>
              {/* Stacked bar */}
              <div className="mb-6 flex h-3 overflow-hidden rounded-full">
                {statusRows.map((s) => (
                  <motion.div
                    key={s.status}
                    initial={{ width: 0 }}
                    animate={{ width: `${(s.n / totalStatuses) * 100}%` }}
                    transition={{ duration: 0.7, ease: 'easeOut' }}
                    className={statusColor[s.status]}
                    title={`${s.status}: ${s.n}`}
                  />
                ))}
              </div>

              <ul className="flex flex-col gap-3">
                {statusRows.map((s) => (
                  <li key={s.status} className="flex items-center justify-between gap-3">
                    <span className="flex items-center gap-2 text-[12px] capitalize text-secondary">
                      <span className={`h-2.5 w-2.5 rounded-full ${statusColor[s.status]}`} />
                      {s.status}
                    </span>
                    <span className="text-[12px] text-white">
                      {s.n}
                      <span className="ml-1.5 text-[11px] text-muted">
                        ({Math.round((s.n / totalStatuses) * 100)}%)
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      </div>
    </>
  );
}
