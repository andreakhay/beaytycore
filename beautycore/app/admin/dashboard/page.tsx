'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Wallet,
  CalendarDays,
  Users,
  AlertTriangle,
  ArrowRight,
  Package,
  Clock,
} from 'lucide-react';
import {
  PageHeader,
  Card,
  StatusBadge,
  Skeleton,
  EmptyState,
  formatDate,
  formatTime,
  formatPeso,
} from '@/components/ui';
import AnimatedCounter from '@/components/AnimatedCounter';
import type { AppointmentStatus, ProductStatus } from '@/db/schema';

interface Stats {
  totalRevenue: number;
  monthRevenue: number;
  totalBookings: number;
  activeStylists: number;
  totalClients: number;
  lowStockCount: number;
}

interface LowStockItem {
  id: string;
  productName: string;
  category: string;
  currentStock: number;
  minimumThreshold: number;
  status: ProductStatus;
}

interface AppointmentRow {
  id: string;
  serviceName: string;
  appointmentDate: string;
  status: AppointmentStatus;
  totalPrice: number | null;
  client: { name: string } | null;
  stylist: { name: string } | null;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [lowStock, setLowStock] = useState<LowStockItem[]>([]);
  const [appointments, setAppointments] = useState<AppointmentRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/admin/stats').then((r) => r.json()),
      fetch('/api/appointments').then((r) => r.json()),
    ])
      .then(([s, a]) => {
        setStats(s.stats ?? null);
        setLowStock(s.lowStockItems ?? []);
        setAppointments(a.appointments ?? []);
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  const metrics = [
    {
      label: 'Total Revenue',
      value: stats?.totalRevenue ?? 0,
      prefix: '₱',
      icon: Wallet,
      note: `${formatPeso(stats?.monthRevenue ?? 0)} this month`,
      accent: 'text-gold',
    },
    {
      label: 'Total Bookings',
      value: stats?.totalBookings ?? 0,
      icon: CalendarDays,
      note: `${stats?.totalClients ?? 0} clients`,
      accent: 'text-info',
    },
    {
      label: 'Active Stylists',
      value: stats?.activeStylists ?? 0,
      icon: Users,
      note: 'On the team',
      accent: 'text-success',
    },
    {
      label: 'Low Stock Items',
      value: stats?.lowStockCount ?? 0,
      icon: AlertTriangle,
      note: 'At or below threshold',
      accent: (stats?.lowStockCount ?? 0) > 0 ? 'text-error' : 'text-muted',
    },
  ];

  const recent = [...appointments]
    .sort(
      (a, b) =>
        new Date(b.appointmentDate).getTime() - new Date(a.appointmentDate).getTime()
    )
    .slice(0, 8);

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Everything happening at Andrea's, at a glance."
      />

      {/* Metrics */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {loading
          ? [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-32 w-full" />)
          : metrics.map((m, i) => (
              <motion.div
                key={m.label}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
              >
                <Card>
                  <div className="mb-3 flex items-start justify-between">
                    <span className="text-[10px] font-semibold uppercase tracking-[1.5px] text-muted">
                      {m.label}
                    </span>
                    <m.icon size={16} className={m.accent} />
                  </div>
                  <p className={`mb-1.5 font-serif text-3xl ${m.accent}`}>
                    <AnimatedCounter value={m.value} prefix={m.prefix} />
                  </p>
                  <p className="text-[11px] text-muted">{m.note}</p>
                </Card>
              </motion.div>
            ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        {/* Appointment monitor */}
        <Card>
          <div className="mb-5 flex items-center justify-between">
            <h2 className="font-serif text-xl text-white">Recent Appointments</h2>
            <Link
              href="/admin/appointments"
              className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[1.5px] text-gold hover:underline"
            >
              Manage
              <ArrowRight size={11} />
            </Link>
          </div>

          {loading ? (
            <div className="flex flex-col gap-2">
              {[0, 1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : recent.length === 0 ? (
            <EmptyState icon={CalendarDays} title="No appointments yet" />
          ) : (
            <div className="scrollbar-thin overflow-x-auto">
              <table className="w-full min-w-[560px]">
                <thead>
                  <tr className="border-b border-purple-light/15">
                    {['Client', 'Service', 'Stylist', 'When', 'Status'].map((h) => (
                      <th
                        key={h}
                        className="pb-3 text-left text-[10px] font-semibold uppercase tracking-[1.5px] text-muted"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recent.map((a) => (
                    <tr
                      key={a.id}
                      className="border-b border-white/[0.04] last:border-0"
                    >
                      <td className="py-3 text-[12px] text-white">
                        {a.client?.name ?? '—'}
                      </td>
                      <td className="py-3 text-[12px] text-secondary">
                        {a.serviceName}
                      </td>
                      <td className="py-3 text-[12px] text-muted">
                        {a.stylist?.name ?? 'Unassigned'}
                      </td>
                      <td className="py-3 text-[11px] text-muted">
                        <span className="block">{formatDate(a.appointmentDate)}</span>
                        <span className="flex items-center gap-1">
                          <Clock size={10} />
                          {formatTime(a.appointmentDate)}
                        </span>
                      </td>
                      <td className="py-3">
                        <StatusBadge status={a.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Inventory alerts */}
        <Card>
          <div className="mb-5 flex items-center justify-between">
            <h2 className="flex items-center gap-2 font-serif text-xl text-white">
              <AlertTriangle size={16} className="text-warning" />
              Stock Alerts
            </h2>
            <Link
              href="/admin/inventory"
              className="text-[10px] font-semibold uppercase tracking-[1.5px] text-gold hover:underline"
            >
              All
            </Link>
          </div>

          {loading ? (
            <div className="flex flex-col gap-2">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : lowStock.length === 0 ? (
            <EmptyState icon={Package} title="All stocked up" body="Nothing below threshold." />
          ) : (
            <ul className="flex flex-col gap-2.5">
              {lowStock.map((item) => {
                const out = item.status === 'out_of_stock';
                return (
                  <li
                    key={item.id}
                    className={`rounded-sm border p-3 ${
                      out
                        ? 'border-error/30 bg-error/10'
                        : 'border-warning/25 bg-warning/5'
                    }`}
                  >
                    <div className="mb-1 flex items-start justify-between gap-3">
                      <span className="text-[12px] font-medium text-white">
                        {item.productName}
                      </span>
                      <span
                        className={`shrink-0 text-[11px] font-medium ${
                          out ? 'text-error' : 'text-warning'
                        }`}
                      >
                        {item.currentStock} left
                      </span>
                    </div>
                    <p className="text-[10px] text-muted">
                      {item.category} · threshold {item.minimumThreshold}
                    </p>
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
