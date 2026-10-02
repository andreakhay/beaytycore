'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  CalendarDays,
  Clock,
  Users,
  CheckCircle2,
  ArrowRight,
  Sun,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import {
  Card,
  StatusBadge,
  EmptyState,
  Skeleton,
  formatDate,
  formatTime,
  formatPeso,
} from '@/components/ui';
import AnimatedCounter from '@/components/AnimatedCounter';
import type { AppointmentStatus } from '@/db/schema';

interface Row {
  id: string;
  serviceName: string;
  appointmentDate: string;
  status: AppointmentStatus;
  totalPrice: number | null;
  notes: string | null;
  client: { id: string; name: string; email: string } | null;
}

const isSameDay = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() &&
  a.getMonth() === b.getMonth() &&
  a.getDate() === b.getDate();

export default function StylistDashboard() {
  const { user } = useAuth();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/appointments')
      .then((r) => r.json())
      .then((d) => setRows(d.appointments ?? []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, []);

  const now = new Date();
  const today = rows
    .filter((r) => isSameDay(new Date(r.appointmentDate), now) && r.status !== 'cancelled')
    .sort(
      (a, b) =>
        new Date(a.appointmentDate).getTime() - new Date(b.appointmentDate).getTime()
    );

  const upcoming = rows
    .filter(
      (r) => new Date(r.appointmentDate).getTime() > now.getTime() && r.status !== 'cancelled'
    )
    .sort(
      (a, b) =>
        new Date(a.appointmentDate).getTime() - new Date(b.appointmentDate).getTime()
    );

  const completed = rows.filter((r) => r.status === 'completed');
  const uniqueClients = new Set(rows.map((r) => r.client?.id).filter(Boolean)).size;
  const earned = completed.reduce((sum, r) => sum + (r.totalPrice ?? 0), 0);

  const metrics = [
    { label: "Today's Appointments", value: today.length, icon: Sun, accent: 'text-gold' },
    { label: 'Upcoming', value: upcoming.length, icon: CalendarDays, accent: 'text-info' },
    { label: 'Clients Served', value: uniqueClients, icon: Users, accent: 'text-purple-glow' },
    { label: 'Completed', value: completed.length, icon: CheckCircle2, accent: 'text-success' },
  ];

  const firstName = user?.name?.split(' ')[0] ?? '';

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-8"
      >
        <h1 className="font-serif text-3xl text-white">
          Good day{firstName && `, ${firstName}`}
        </h1>
        <p className="mt-1.5 text-[13px] text-muted">
          {today.length > 0
            ? `You have ${today.length} appointment${today.length > 1 ? 's' : ''} today.`
            : 'Nothing on your schedule today.'}
        </p>
      </motion.div>

      {/* Metrics */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {loading
          ? [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-28 w-full" />)
          : metrics.map((m, i) => (
              <motion.div
                key={m.label}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: i * 0.07 }}
              >
                <Card>
                  <div className="mb-2.5 flex items-start justify-between">
                    <span className="text-[10px] font-semibold uppercase tracking-[1.5px] text-muted">
                      {m.label}
                    </span>
                    <m.icon size={15} className={m.accent} />
                  </div>
                  <p className={`font-serif text-3xl ${m.accent}`}>
                    <AnimatedCounter value={m.value} />
                  </p>
                </Card>
              </motion.div>
            ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Today */}
        <Card>
          <div className="mb-5 flex items-center justify-between">
            <h2 className="flex items-center gap-2 font-serif text-xl text-white">
              <Sun size={17} className="text-gold" />
              Today&apos;s Schedule
            </h2>
            <Link
              href="/stylist/appointments"
              className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[1.5px] text-gold hover:underline"
            >
              All
              <ArrowRight size={11} />
            </Link>
          </div>

          {loading ? (
            <div className="flex flex-col gap-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : today.length === 0 ? (
            <EmptyState
              icon={Sun}
              title="Nothing booked today"
              body="Enjoy the quiet — or check what's coming up."
            />
          ) : (
            <ul className="flex flex-col gap-3">
              {today.map((r) => (
                <li
                  key={r.id}
                  className="flex items-start gap-4 rounded-sm border border-purple-light/10 bg-surface/25 p-4"
                >
                  <div className="shrink-0 text-center">
                    <p className="font-serif text-lg text-gold">
                      {formatTime(r.appointmentDate).replace(/\s?[AP]M/i, '')}
                    </p>
                    <p className="text-[9px] uppercase text-muted">
                      {formatTime(r.appointmentDate).match(/[AP]M/i)?.[0]}
                    </p>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="mb-0.5 truncate text-[13px] font-medium text-white">
                      {r.serviceName}
                    </p>
                    <p className="truncate text-[11px] text-muted">
                      {r.client?.name ?? 'Unknown client'}
                    </p>
                    {r.notes && (
                      <p className="mt-1.5 text-[11px] leading-relaxed text-secondary">
                        {r.notes}
                      </p>
                    )}
                  </div>
                  <StatusBadge status={r.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Upcoming */}
        <Card>
          <h2 className="mb-5 font-serif text-xl text-white">Coming Up</h2>

          {loading ? (
            <div className="flex flex-col gap-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : upcoming.length === 0 ? (
            <EmptyState icon={CalendarDays} title="No upcoming appointments" />
          ) : (
            <ul className="flex flex-col gap-3">
              {upcoming.slice(0, 5).map((r) => (
                <li
                  key={r.id}
                  className="flex items-start justify-between gap-4 rounded-sm border border-purple-light/10 bg-surface/25 p-4"
                >
                  <div className="min-w-0">
                    <p className="mb-0.5 truncate text-[13px] font-medium text-white">
                      {r.serviceName}
                    </p>
                    <p className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-muted">
                      <span>{r.client?.name}</span>
                      <span className="flex items-center gap-1">
                        <CalendarDays size={10} />
                        {formatDate(r.appointmentDate)}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock size={10} />
                        {formatTime(r.appointmentDate)}
                      </span>
                    </p>
                  </div>
                  <span className="shrink-0 text-[12px] text-white">
                    {formatPeso(r.totalPrice)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* Earnings note */}
      {!loading && completed.length > 0 && (
        <Card className="mt-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-[1.5px] text-muted">
                Revenue from Completed Services
              </p>
              <p className="font-serif text-3xl text-gold">{formatPeso(earned)}</p>
            </div>
            <p className="max-w-xs text-[11px] leading-relaxed text-muted">
              Across {completed.length} completed appointment
              {completed.length !== 1 ? 's' : ''} assigned to you.
            </p>
          </div>
        </Card>
      )}
    </>
  );
}
