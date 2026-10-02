'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Save, Loader2, CheckCircle, AlertCircle, Award } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { PageHeader, Card, Skeleton, formatDate } from '@/components/ui';

interface ProfileData {
  id: string;
  name: string;
  email: string;
  role: string;
  createdAt: string;
}

export default function StylistProfilePage() {
  const { refresh } = useAuth();
  const [data, setData] = useState<ProfileData | null>(null);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState({ total: 0, completed: 0, clients: 0 });

  useEffect(() => {
    Promise.all([
      fetch('/api/profile').then((r) => r.json()),
      fetch('/api/appointments').then((r) => r.json()),
    ])
      .then(([p, a]) => {
        if (p.user) {
          setData(p.user);
          setName(p.user.name ?? '');
        }
        const rows = a.appointments ?? [];
        setStats({
          total: rows.length,
          completed: rows.filter(
            (r: { status: string }) => r.status === 'completed'
          ).length,
          clients: new Set(
            rows.map((r: { client?: { id: string } }) => r.client?.id).filter(Boolean)
          ).size,
        });
      })
      .catch(() => setError('Could not load your profile.'))
      .finally(() => setLoading(false));
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSaved(false);

    try {
      const res = await fetch('/api/profile', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.error ?? 'Could not save.');

      setData(d.user);
      await refresh();
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save changes.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <>
        <PageHeader title="My Profile" />
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </>
    );
  }

  const initials = (data?.name ?? '')
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <>
      <PageHeader title="My Profile" subtitle="Your account and performance." />

      {error && (
        <div className="mb-6 flex items-start gap-2 rounded-sm border border-error/30 bg-error/10 p-4 text-[13px] text-error">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {saved && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 flex items-center gap-2 rounded-sm border border-success/30 bg-success/10 p-4 text-[13px] text-success"
        >
          <CheckCircle size={16} />
          Saved.
        </motion.div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <form onSubmit={save}>
            <div className="mb-6 flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-purple text-lg font-semibold text-white">
                {initials || '··'}
              </div>
              <div>
                <p className="text-[15px] font-medium text-white">{data?.name}</p>
                <p className="text-[12px] capitalize text-muted">{data?.role}</p>
              </div>
            </div>

            <div className="mb-4">
              <label htmlFor="name" className="mb-1.5 block text-[11px] font-medium text-secondary">
                Full Name
              </label>
              <input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full rounded-sm border border-purple-light/20 bg-surface/40 px-4 py-2.5 text-[13px] text-white focus:border-purple-light focus:outline-none"
              />
            </div>

            <div className="mb-6">
              <label className="mb-1.5 block text-[11px] font-medium text-secondary">
                Email
              </label>
              <input
                value={data?.email ?? ''}
                disabled
                className="w-full cursor-not-allowed rounded-sm border border-purple-light/10 bg-surface/20 px-4 py-2.5 text-[13px] text-muted"
              />
              <p className="mt-1.5 text-[11px] text-muted">
                Ask an admin to change your email or role.
              </p>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 bg-gold px-6 py-3 text-[11px] font-semibold uppercase tracking-[2px] text-card transition-colors hover:bg-gold-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  <Save size={14} />
                  Save Changes
                </>
              )}
            </button>
          </form>
        </Card>

        <Card>
          <h2 className="mb-5 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[2px] text-gold">
            <Award size={12} />
            Your Numbers
          </h2>

          <div className="mb-6 grid grid-cols-3 gap-4">
            {[
              { label: 'Assigned', value: stats.total },
              { label: 'Completed', value: stats.completed },
              { label: 'Clients', value: stats.clients },
            ].map((s) => (
              <div key={s.label}>
                <p className="mb-1 font-serif text-3xl text-white">{s.value}</p>
                <p className="text-[10px] uppercase tracking-wide text-muted">
                  {s.label}
                </p>
              </div>
            ))}
          </div>

          <div className="border-t border-purple-light/10 pt-4">
            <p className="mb-1 text-[10px] uppercase tracking-wide text-muted">
              Member since
            </p>
            <p className="text-[13px] text-secondary">
              {data?.createdAt ? formatDate(data.createdAt) : '—'}
            </p>
          </div>
        </Card>
      </div>
    </>
  );
}
