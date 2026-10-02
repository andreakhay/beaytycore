'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { CalendarDays, Clock, User, X, Loader2 } from 'lucide-react';
import {
  PageHeader,
  Card,
  StatusBadge,
  EmptyState,
  Skeleton,
  formatDate,
  formatTime,
  formatPeso,
} from '@/components/ui';
import type { AppointmentStatus } from '@/db/schema';

interface Row {
  id: string;
  serviceName: string;
  serviceType: string;
  appointmentDate: string;
  status: AppointmentStatus;
  totalPrice: number | null;
  notes: string | null;
  stylist: { id: string; name: string } | null;
}

type Filter = 'upcoming' | 'past' | 'all';

export default function ClientAppointmentsPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>('upcoming');
  const [cancelling, setCancelling] = useState<string | null>(null);

  const load = () => {
    fetch('/api/appointments')
      .then((r) => r.json())
      .then((d) => setRows(d.appointments ?? []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const cancel = async (id: string) => {
    if (!confirm('Cancel this appointment?')) return;
    setCancelling(id);
    try {
      const res = await fetch(`/api/appointments/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'cancelled' }),
      });
      if (res.ok) load();
    } finally {
      setCancelling(null);
    }
  };

  const now = Date.now();
  const filtered = rows.filter((r) => {
    const t = new Date(r.appointmentDate).getTime();
    if (filter === 'upcoming') return t >= now && r.status !== 'cancelled';
    if (filter === 'past') return t < now || r.status === 'cancelled';
    return true;
  });

  const filters: Array<{ key: Filter; label: string }> = [
    { key: 'upcoming', label: 'Upcoming' },
    { key: 'past', label: 'Past' },
    { key: 'all', label: 'All' },
  ];

  return (
    <>
      <PageHeader
        title="My Appointments"
        subtitle="Everything you've booked with us."
        action={
          <Link
            href="/booking"
            className="bg-gold px-5 py-2.5 text-[10px] font-semibold uppercase tracking-[1.5px] text-card transition-colors hover:bg-gold-hover"
          >
            Book New
          </Link>
        }
      />

      {/* Filters */}
      <div className="mb-6 flex gap-1 rounded-sm border border-purple-light/15 bg-surface/30 p-1">
        {filters.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`relative flex-1 rounded-sm py-2 text-[11px] font-medium uppercase tracking-[1.5px] transition-colors ${
              filter === f.key ? 'text-white' : 'text-muted hover:text-secondary'
            }`}
          >
            {filter === f.key && (
              <motion.span
                layoutId="appt-filter"
                className="absolute inset-0 rounded-sm bg-purple/30"
              />
            )}
            <span className="relative">{f.label}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex flex-col gap-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState
            icon={CalendarDays}
            title={filter === 'upcoming' ? 'No upcoming appointments' : 'Nothing here'}
            body={
              filter === 'upcoming'
                ? 'Book a service and it will appear here.'
                : 'Try a different filter.'
            }
            action={
              filter === 'upcoming' ? (
                <Link
                  href="/booking"
                  className="bg-gold px-5 py-2.5 text-[10px] font-semibold uppercase tracking-[1.5px] text-card transition-colors hover:bg-gold-hover"
                >
                  Book Now
                </Link>
              ) : undefined
            }
          />
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((r, i) => {
            const isUpcoming =
              new Date(r.appointmentDate).getTime() >= now && r.status !== 'cancelled';
            return (
              <motion.div
                key={r.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: Math.min(i * 0.05, 0.3) }}
              >
                <Card className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="mb-2 flex flex-wrap items-center gap-3">
                      <h3 className="font-serif text-lg text-white">{r.serviceName}</h3>
                      <StatusBadge status={r.status} />
                    </div>
                    <p className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-muted">
                      <span className="flex items-center gap-1.5">
                        <CalendarDays size={12} />
                        {formatDate(r.appointmentDate)}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Clock size={12} />
                        {formatTime(r.appointmentDate)}
                      </span>
                      {r.stylist && (
                        <span className="flex items-center gap-1.5">
                          <User size={12} />
                          {r.stylist.name}
                        </span>
                      )}
                    </p>
                    {r.notes && (
                      <p className="mt-2 rounded-sm border border-purple-light/10 bg-surface/25 p-2.5 text-[12px] leading-relaxed text-secondary">
                        {r.notes}
                      </p>
                    )}
                  </div>

                  <div className="flex shrink-0 flex-col items-end gap-2.5">
                    <span className="text-[15px] font-medium text-white">
                      {formatPeso(r.totalPrice)}
                    </span>
                    {isUpcoming && (
                      <button
                        onClick={() => cancel(r.id)}
                        disabled={cancelling === r.id}
                        className="flex items-center gap-1.5 border border-error/30 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[1.5px] text-error transition-colors hover:bg-error/10 disabled:opacity-50"
                      >
                        {cancelling === r.id ? (
                          <Loader2 size={11} className="animate-spin" />
                        ) : (
                          <X size={11} />
                        )}
                        Cancel
                      </button>
                    )}
                  </div>
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}
    </>
  );
}
