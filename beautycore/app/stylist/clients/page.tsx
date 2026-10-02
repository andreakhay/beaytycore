'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Search, Users, Mail, CalendarDays, Repeat } from 'lucide-react';
import {
  PageHeader,
  Card,
  EmptyState,
  Skeleton,
  formatDate,
  formatPeso,
} from '@/components/ui';
import type { AppointmentStatus } from '@/db/schema';

interface Row {
  id: string;
  serviceName: string;
  appointmentDate: string;
  status: AppointmentStatus;
  totalPrice: number | null;
  client: { id: string; name: string; email: string } | null;
}

interface ClientSummary {
  id: string;
  name: string;
  email: string;
  visits: number;
  lastVisit: string;
  totalSpent: number;
  services: string[];
}

/**
 * Stylists see clients derived from their own appointments, not the full
 * directory — they should only know about people they actually serve.
 */
export default function StylistClientsPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');

  useEffect(() => {
    fetch('/api/appointments')
      .then((r) => r.json())
      .then((d) => setRows(d.appointments ?? []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, []);

  const clients = useMemo(() => {
    const map = new Map<string, ClientSummary>();

    for (const r of rows) {
      if (!r.client) continue;
      const existing = map.get(r.client.id);

      if (existing) {
        existing.visits += 1;
        if (r.status === 'completed') existing.totalSpent += r.totalPrice ?? 0;
        if (new Date(r.appointmentDate) > new Date(existing.lastVisit)) {
          existing.lastVisit = r.appointmentDate;
        }
        if (!existing.services.includes(r.serviceName)) {
          existing.services.push(r.serviceName);
        }
      } else {
        map.set(r.client.id, {
          id: r.client.id,
          name: r.client.name,
          email: r.client.email,
          visits: 1,
          lastVisit: r.appointmentDate,
          totalSpent: r.status === 'completed' ? (r.totalPrice ?? 0) : 0,
          services: [r.serviceName],
        });
      }
    }

    return Array.from(map.values()).sort(
      (a, b) => new Date(b.lastVisit).getTime() - new Date(a.lastVisit).getTime()
    );
  }, [rows]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return clients;
    return clients.filter(
      (c) => c.name.toLowerCase().includes(q) || c.email.toLowerCase().includes(q)
    );
  }, [clients, query]);

  const initials = (name: string) =>
    name
      .split(' ')
      .map((n) => n[0])
      .slice(0, 2)
      .join('')
      .toUpperCase();

  return (
    <>
      <PageHeader
        title="My Clients"
        subtitle={`${clients.length} clients you've worked with`}
      />

      <div className="relative mb-6 max-w-md">
        <Search
          size={14}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search clients…"
          className="w-full rounded-sm border border-purple-light/20 bg-surface/40 py-2.5 pl-9 pr-4 text-[13px] text-white placeholder-muted focus:border-purple-light focus:outline-none"
        />
      </div>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState
            icon={Users}
            title={query ? 'No clients match' : 'No clients yet'}
            body={
              query
                ? 'Try a different search.'
                : 'Clients appear here once appointments are assigned to you.'
            }
          />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((c, i) => (
            <motion.div
              key={c.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(i * 0.05, 0.3) }}
            >
              <Card className="h-full">
                <div className="mb-4 flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-purple text-[13px] font-semibold text-white">
                    {initials(c.name)}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-[14px] font-medium text-white">{c.name}</p>
                    <p className="flex items-center gap-1 truncate text-[11px] text-muted">
                      <Mail size={10} />
                      {c.email}
                    </p>
                  </div>
                </div>

                <div className="mb-4 grid grid-cols-2 gap-3 border-t border-purple-light/10 pt-4">
                  <div>
                    <p className="mb-0.5 flex items-center gap-1 text-[10px] uppercase tracking-wide text-muted">
                      <Repeat size={9} />
                      Visits
                    </p>
                    <p className="text-[15px] text-white">{c.visits}</p>
                  </div>
                  <div>
                    <p className="mb-0.5 text-[10px] uppercase tracking-wide text-muted">
                      Revenue
                    </p>
                    <p className="text-[15px] text-gold">{formatPeso(c.totalSpent)}</p>
                  </div>
                </div>

                <div className="mb-3 flex flex-wrap gap-1.5">
                  {c.services.slice(0, 3).map((s) => (
                    <span
                      key={s}
                      className="rounded-full border border-purple-light/20 px-2 py-0.5 text-[10px] text-muted"
                    >
                      {s}
                    </span>
                  ))}
                  {c.services.length > 3 && (
                    <span className="px-1 py-0.5 text-[10px] text-muted">
                      +{c.services.length - 3}
                    </span>
                  )}
                </div>

                <p className="flex items-center gap-1.5 text-[10px] text-muted">
                  <CalendarDays size={10} />
                  Last seen {formatDate(c.lastVisit)}
                </p>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </>
  );
}
