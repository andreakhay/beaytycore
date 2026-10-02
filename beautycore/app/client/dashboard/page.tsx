'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Sparkles,
  CalendarDays,
  Hand,
  Scissors,
  ArrowRight,
  Clock,
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
import type { AppointmentStatus, StyleType } from '@/db/schema';

interface AppointmentRow {
  id: string;
  serviceName: string;
  serviceType: string;
  appointmentDate: string;
  status: AppointmentStatus;
  totalPrice: number | null;
  stylist: { id: string; name: string } | null;
}

interface GenerationRow {
  id: string;
  promptText: string;
  generatedImageUrl: string | null;
  styleType: StyleType;
  analysisResult: {
    recommendations?: Array<{ title: string }>;
  } | null;
  createdAt: string;
}

const quickActions = [
  {
    href: '/client/ai-advisor',
    icon: Sparkles,
    title: 'AI Advisor',
    body: 'Upload a photo, get three styles picked for you',
  },
  {
    href: '/booking',
    icon: CalendarDays,
    title: 'Book',
    body: 'Reserve your next appointment',
  },
  {
    href: '/client/nail-studio',
    icon: Hand,
    title: 'Nail Studio',
    body: 'Browse designs and build your own',
  },
  {
    href: '/client/hair-studio',
    icon: Scissors,
    title: 'Hair Studio',
    body: 'Explore cuts, colour, and treatments',
  },
];

export default function ClientDashboard() {
  const { user } = useAuth();
  const [appointments, setAppointments] = useState<AppointmentRow[]>([]);
  const [generations, setGenerations] = useState<GenerationRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/appointments').then((r) => r.json()),
      fetch('/api/generations').then((r) => r.json()),
    ])
      .then(([a, g]) => {
        setAppointments(a.appointments ?? []);
        setGenerations(g.generations ?? []);
      })
      .catch(() => {
        setAppointments([]);
        setGenerations([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const now = Date.now();
  const upcoming = appointments
    .filter(
      (a) =>
        new Date(a.appointmentDate).getTime() >= now &&
        a.status !== 'cancelled'
    )
    .sort(
      (a, b) =>
        new Date(a.appointmentDate).getTime() - new Date(b.appointmentDate).getTime()
    );

  const firstName = user?.name?.split(' ')[0] ?? '';

  return (
    <>
      {/* Welcome */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-8"
      >
        <h1 className="font-serif text-3xl text-white">
          Welcome back{firstName && `, ${firstName}`}
        </h1>
        <p className="mt-1.5 text-[13px] text-muted">
          {upcoming.length > 0
            ? `You have ${upcoming.length} upcoming appointment${upcoming.length > 1 ? 's' : ''}.`
            : 'No upcoming appointments — book when you’re ready.'}
        </p>
      </motion.div>

      {/* Quick actions */}
      <div className="mb-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {quickActions.map((a, i) => (
          <motion.div
            key={a.href}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: i * 0.06 }}
          >
            <Link
              href={a.href}
              className="group flex h-full flex-col rounded-sm border border-purple-light/15 bg-card p-5 transition-colors hover:border-gold/40"
            >
              <div className="mb-3.5 inline-flex h-10 w-10 items-center justify-center rounded-full border border-gold/25 bg-gold/10">
                <a.icon size={17} className="text-gold" />
              </div>
              <h3 className="mb-1.5 font-serif text-base text-white">{a.title}</h3>
              <p className="mb-3 flex-1 text-[12px] leading-relaxed text-muted">
                {a.body}
              </p>
              <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[1.5px] text-gold">
                Open
                <ArrowRight
                  size={11}
                  className="transition-transform group-hover:translate-x-1"
                />
              </span>
            </Link>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upcoming appointments */}
        <Card>
          <div className="mb-5 flex items-center justify-between">
            <h2 className="font-serif text-xl text-white">Upcoming</h2>
            <Link
              href="/client/appointments"
              className="text-[10px] font-semibold uppercase tracking-[1.5px] text-gold hover:underline"
            >
              View all
            </Link>
          </div>

          {loading ? (
            <div className="flex flex-col gap-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : upcoming.length === 0 ? (
            <EmptyState
              icon={CalendarDays}
              title="Nothing booked yet"
              body="Your next appointment will show up here."
              action={
                <Link
                  href="/booking"
                  className="bg-gold px-5 py-2.5 text-[10px] font-semibold uppercase tracking-[1.5px] text-card transition-colors hover:bg-gold-hover"
                >
                  Book Now
                </Link>
              }
            />
          ) : (
            <ul className="flex flex-col gap-3">
              {upcoming.slice(0, 4).map((a) => (
                <li
                  key={a.id}
                  className="flex items-start justify-between gap-4 rounded-sm border border-purple-light/10 bg-surface/25 p-4"
                >
                  <div className="min-w-0">
                    <p className="mb-1 truncate text-[13px] font-medium text-white">
                      {a.serviceName}
                    </p>
                    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted">
                      <span className="flex items-center gap-1">
                        <CalendarDays size={11} />
                        {formatDate(a.appointmentDate)}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock size={11} />
                        {formatTime(a.appointmentDate)}
                      </span>
                      {a.stylist && <span>with {a.stylist.name}</span>}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1.5">
                    <StatusBadge status={a.status} />
                    <span className="text-[11px] text-muted">
                      {formatPeso(a.totalPrice)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Recent AI recommendations */}
        <Card>
          <div className="mb-5 flex items-center justify-between">
            <h2 className="font-serif text-xl text-white">Recent AI Looks</h2>
            <Link
              href="/client/ai-advisor"
              className="text-[10px] font-semibold uppercase tracking-[1.5px] text-gold hover:underline"
            >
              New analysis
            </Link>
          </div>

          {loading ? (
            <div className="flex flex-col gap-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : generations.length === 0 ? (
            <EmptyState
              icon={Sparkles}
              title="No analyses yet"
              body="Upload a photo of your hair or nails and the AI will suggest three styles that suit it."
              action={
                <Link
                  href="/client/ai-advisor"
                  className="bg-gold px-5 py-2.5 text-[10px] font-semibold uppercase tracking-[1.5px] text-card transition-colors hover:bg-gold-hover"
                >
                  Try the Advisor
                </Link>
              }
            />
          ) : (
            <ul className="flex flex-col gap-3">
              {generations.slice(0, 4).map((g) => {
                const title =
                  g.analysisResult?.recommendations?.[0]?.title ??
                  g.promptText.slice(0, 48);
                return (
                  <li
                    key={g.id}
                    className="flex items-center gap-4 rounded-sm border border-purple-light/10 bg-surface/25 p-4"
                  >
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-sm border border-purple-light/20 bg-purple/15">
                      {g.styleType === 'nail' ? (
                        <Hand size={16} className="text-purple-glow" />
                      ) : (
                        <Scissors size={16} className="text-purple-glow" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13px] font-medium text-white">
                        {title}
                      </p>
                      <p className="text-[11px] capitalize text-muted">
                        {g.styleType} · {formatDate(g.createdAt)}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
