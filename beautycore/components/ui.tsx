import type { ReactNode } from 'react';
import type { AppointmentStatus } from '@/db/schema';

// ─── Page header ────────────────────────────────────────────────────────────

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-serif text-3xl text-white">{title}</h1>
        {subtitle && <p className="mt-1.5 text-[13px] text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

// ─── Card ───────────────────────────────────────────────────────────────────

export function Card({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-sm border border-purple-light/15 bg-card p-6 ${className}`}
    >
      {children}
    </div>
  );
}

// ─── Status badge ───────────────────────────────────────────────────────────

const statusStyles: Record<AppointmentStatus, { bg: string; text: string; label: string }> = {
  confirmed: { bg: 'bg-success/15 border-success/30', text: 'text-success', label: 'Confirmed' },
  pending: { bg: 'bg-warning/15 border-warning/30', text: 'text-warning', label: 'Pending' },
  cancelled: { bg: 'bg-error/15 border-error/30', text: 'text-error', label: 'Cancelled' },
  completed: { bg: 'bg-info/15 border-info/30', text: 'text-info', label: 'Completed' },
};

export function StatusBadge({ status }: { status: AppointmentStatus }) {
  const s = statusStyles[status] ?? statusStyles.pending;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${s.bg} ${s.text}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {s.label}
    </span>
  );
}

// ─── Empty state ────────────────────────────────────────────────────────────

export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
}: {
  icon?: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-sm border border-dashed border-purple-light/20 px-6 py-16 text-center">
      {Icon && (
        <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full border border-purple-light/20 bg-surface/40">
          <Icon size={20} className="text-muted" />
        </div>
      )}
      <p className="mb-1.5 font-serif text-lg text-white">{title}</p>
      {body && <p className="mb-5 max-w-sm text-[13px] leading-relaxed text-muted">{body}</p>}
      {action}
    </div>
  );
}

// ─── Loading skeleton ───────────────────────────────────────────────────────

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-sm bg-surface/50 ${className}`} />;
}

export function SkeletonCard() {
  return (
    <Card>
      <Skeleton className="mb-3 h-3 w-24" />
      <Skeleton className="mb-2 h-7 w-32" />
      <Skeleton className="h-3 w-full" />
    </Card>
  );
}

// ─── Formatting ─────────────────────────────────────────────────────────────

export function formatDate(date: Date | string): string {
  return new Date(date).toLocaleDateString('en-PH', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function formatTime(date: Date | string): string {
  return new Date(date).toLocaleTimeString('en-PH', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function formatPeso(amount: number | null | undefined): string {
  if (amount == null) return '—';
  return `₱${amount.toLocaleString('en-PH')}`;
}
