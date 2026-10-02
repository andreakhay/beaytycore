'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Search, CalendarDays, Clock, Loader2, Check } from 'lucide-react';
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
import { appointmentStatusEnum, type AppointmentStatus } from '@/db/schema';

interface Row {
  id: string;
  serviceName: string;
  serviceType: string;
  appointmentDate: string;
  status: AppointmentStatus;
  totalPrice: number | null;
  notes: string | null;
  client: { id: string; name: string; email: string } | null;
}

type Range = 'upcoming' | 'past' | 'all';

export default function StylistAppointmentsPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [range, setRange] = useState<Range>('upcoming');
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/appointments')
      .then((r) => r.json())
      .then((d) => setRows(d.appointments ?? []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, []);

  const setStatus = async (id: string, status: AppointmentStatus) => {
    setBusy(id);
    try {
      const res = await fetch(`/api/appointments/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (res.ok) setRows((rs) => rs.map((r) => (r.id === id ? { ...r, status } : r)));
    } finally {
      setBusy(null);
    }
  };

  const now = Date.now();
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows
      .filter((r) => {
        const t = new Date(r.appointmentDate).getTime();
        if (range === 'upcoming') return t >= now && r.status !== 'cancelled';
        if (range === 'past') return t < now || r.status === 'cancelled';
        return true;
      })
      .filter(
        (r) =>
          !q ||
          r.serviceName.toLowerCase().includes(q) ||
          r.client?.name.toLowerCase().includes(q)
      )
      .sort(
        (a, b) =>
          new Date(a.appointmentDate).getTime() - new Date(b.appointmentDate).getTime()
      );
  }, [rows, query, range, now]);

  return (
    <>
      <PageHeader
        title="My Appointments"
        subtitle={`${rows.length} appointments assigned to you`}
      />

      <div className="mb-6 flex flex-wrap gap-3">
        <div className="relative min-w-[220px] flex-1">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search client or service…"
            className="w-full rounded-sm border border-purple-light/20 bg-surface/40 py-2.5 pl-9 pr-4 text-[13px] text-white placeholder-muted focus:border-purple-light focus:outline-none"
          />
        </div>

        <div className="flex gap-1 rounded-sm border border-purple-light/15 bg-surface/30 p-1">
          {(['upcoming', 'past', 'all'] as const).map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`relative rounded-sm px-4 py-2 text-[11px] font-medium capitalize tracking-[1px] transition-colors ${
                range === r ? 'text-white' : 'text-muted hover:text-secondary'
              }`}
            >
              {range === r && (
                <motion.span
                  layoutId="stylist-range"
                  className="absolute inset-0 rounded-sm bg-purple/30"
                />
              )}
              <span className="relative">{r}</span>
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col gap-3">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState
            icon={CalendarDays}
            title="Nothing here"
            body="Try a different range or search."
          />
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((r, i) => (
            <motion.div
              key={r.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(i * 0.04, 0.25) }}
            >
              <Card className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="mb-2 flex flex-wrap items-center gap-3">
                    <h3 className="font-serif text-lg text-white">{r.serviceName}</h3>
                    <StatusBadge status={r.status} />
                  </div>
                  <p className="mb-1 text-[12px] text-secondary">
                    {r.client?.name ?? 'Unknown client'}
                  </p>
                  <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted">
                    <span className="flex items-center gap-1.5">
                      <CalendarDays size={11} />
                      {formatDate(r.appointmentDate)}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Clock size={11} />
                      {formatTime(r.appointmentDate)}
                    </span>
                    <span className="text-white">{formatPeso(r.totalPrice)}</span>
                  </p>
                  {r.notes && (
                    <p className="mt-2 rounded-sm border border-purple-light/10 bg-surface/25 p-2.5 text-[12px] leading-relaxed text-secondary">
                      {r.notes}
                    </p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  {r.status !== 'completed' && r.status !== 'cancelled' && (
                    <button
                      onClick={() => setStatus(r.id, 'completed')}
                      disabled={busy === r.id}
                      className="flex items-center gap-1.5 border border-success/30 px-3 py-2 text-[10px] font-semibold uppercase tracking-[1.5px] text-success transition-colors hover:bg-success/10 disabled:opacity-50"
                    >
                      {busy === r.id ? (
                        <Loader2 size={11} className="animate-spin" />
                      ) : (
                        <Check size={11} />
                      )}
                      Complete
                    </button>
                  )}
                  <select
                    value={r.status}
                    onChange={(e) => setStatus(r.id, e.target.value as AppointmentStatus)}
                    disabled={busy === r.id}
                    className="rounded-sm border border-purple-light/20 bg-surface/40 px-3 py-2 text-[11px] text-white focus:border-purple-light focus:outline-none disabled:opacity-50"
                  >
                    {appointmentStatusEnum.enumValues.map((s) => (
                      <option key={s} value={s}>
                        {s.charAt(0).toUpperCase() + s.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </>
  );
}
