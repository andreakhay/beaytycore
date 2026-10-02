'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Search, Trash2, Loader2, CalendarDays, Clock } from 'lucide-react';
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
  stylist: { id: string; name: string } | null;
}

export default function AdminAppointmentsPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<AppointmentStatus | 'all'>('all');
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => {
    fetch('/api/appointments')
      .then((r) => r.json())
      .then((d) => setRows(d.appointments ?? []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const setStatus = async (id: string, status: AppointmentStatus) => {
    setBusy(id);
    try {
      const res = await fetch(`/api/appointments/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        setRows((rs) => rs.map((r) => (r.id === id ? { ...r, status } : r)));
      }
    } finally {
      setBusy(null);
    }
  };

  const remove = async (id: string) => {
    if (!confirm('Delete this appointment permanently?')) return;
    setBusy(id);
    try {
      const res = await fetch(`/api/appointments/${id}`, { method: 'DELETE' });
      if (res.ok) setRows((rs) => rs.filter((r) => r.id !== id));
    } finally {
      setBusy(null);
    }
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (statusFilter !== 'all' && r.status !== statusFilter) return false;
      if (!q) return true;
      return (
        r.serviceName.toLowerCase().includes(q) ||
        r.client?.name.toLowerCase().includes(q) ||
        r.client?.email.toLowerCase().includes(q) ||
        r.stylist?.name.toLowerCase().includes(q)
      );
    });
  }, [rows, query, statusFilter]);

  return (
    <>
      <PageHeader
        title="Appointments"
        subtitle={`${rows.length} total · managing all bookings`}
      />

      {/* Controls */}
      <div className="mb-6 flex flex-wrap gap-3">
        <div className="relative min-w-[240px] flex-1">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search client, service, or stylist…"
            className="w-full rounded-sm border border-purple-light/20 bg-surface/40 py-2.5 pl-9 pr-4 text-[13px] text-white placeholder-muted focus:border-purple-light focus:outline-none"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as AppointmentStatus | 'all')}
          className="rounded-sm border border-purple-light/20 bg-surface/40 px-4 py-2.5 text-[13px] text-white focus:border-purple-light focus:outline-none"
        >
          <option value="all">All statuses</option>
          {appointmentStatusEnum.enumValues.map((s) => (
            <option key={s} value={s}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex flex-col gap-3">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState
            icon={CalendarDays}
            title="No appointments match"
            body="Try a different search or filter."
          />
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((r, i) => (
            <motion.div
              key={r.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(i * 0.03, 0.25) }}
            >
              <Card className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="mb-2 flex flex-wrap items-center gap-3">
                    <h3 className="font-serif text-lg text-white">{r.serviceName}</h3>
                    <StatusBadge status={r.status} />
                  </div>
                  <p className="mb-1 text-[12px] text-secondary">
                    {r.client?.name ?? 'Unknown client'}
                    {r.client?.email && (
                      <span className="text-muted"> · {r.client.email}</span>
                    )}
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
                    <span>{r.stylist?.name ?? 'Unassigned'}</span>
                    <span className="text-white">{formatPeso(r.totalPrice)}</span>
                  </p>
                  {r.notes && (
                    <p className="mt-2 rounded-sm border border-purple-light/10 bg-surface/25 p-2.5 text-[12px] text-secondary">
                      {r.notes}
                    </p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-2">
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

                  <button
                    onClick={() => remove(r.id)}
                    disabled={busy === r.id}
                    aria-label="Delete appointment"
                    className="rounded-sm border border-error/30 p-2 text-error transition-colors hover:bg-error/10 disabled:opacity-50"
                  >
                    {busy === r.id ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      <Trash2 size={13} />
                    )}
                  </button>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </>
  );
}
