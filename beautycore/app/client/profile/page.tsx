'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Save, Loader2, CheckCircle, AlertCircle, Sparkles } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { PageHeader, Card, Skeleton, formatDate } from '@/components/ui';

interface ProfileData {
  id: string;
  name: string;
  email: string;
  role: string;
  avatar: string | null;
  profile: {
    hairPreferences: string | null;
    nailPreferences: string | null;
    styleHistory: Array<{ date: string; type: string; description: string }> | null;
  } | null;
}

export default function ClientProfilePage() {
  const { refresh } = useAuth();
  const [data, setData] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  const [name, setName] = useState('');
  const [hairPreferences, setHair] = useState('');
  const [nailPreferences, setNail] = useState('');

  useEffect(() => {
    fetch('/api/profile')
      .then((r) => r.json())
      .then((d) => {
        if (d.user) {
          setData(d.user);
          setName(d.user.name ?? '');
          setHair(d.user.profile?.hairPreferences ?? '');
          setNail(d.user.profile?.nailPreferences ?? '');
        }
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
        body: JSON.stringify({ name, hairPreferences, nailPreferences }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.error ?? 'Could not save.');

      setData(d.user);
      await refresh(); // keep the sidebar name in sync
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
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-72 w-full" />
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
      <PageHeader title="My Profile" subtitle="Your details and style preferences." />

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

      <form onSubmit={save} className="grid gap-6 lg:grid-cols-2">
        {/* Account */}
        <Card>
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

          <div>
            <label className="mb-1.5 block text-[11px] font-medium text-secondary">
              Email
            </label>
            <input
              value={data?.email ?? ''}
              disabled
              className="w-full cursor-not-allowed rounded-sm border border-purple-light/10 bg-surface/20 px-4 py-2.5 text-[13px] text-muted"
            />
            <p className="mt-1.5 text-[11px] text-muted">
              Contact us if you need to change your email.
            </p>
          </div>
        </Card>

        {/* Preferences */}
        <Card>
          <h2 className="mb-5 text-[10px] font-semibold uppercase tracking-[2px] text-gold">
            Style Preferences
          </h2>
          <p className="mb-5 text-[12px] leading-relaxed text-muted">
            Tell your stylist what you like and what to avoid. This shows up on
            your appointments.
          </p>

          <div className="mb-4">
            <label htmlFor="hair" className="mb-1.5 block text-[11px] font-medium text-secondary">
              Hair
            </label>
            <textarea
              id="hair"
              value={hairPreferences}
              onChange={(e) => setHair(e.target.value)}
              rows={3}
              maxLength={2000}
              placeholder="Warm tones, no heavy bleach, shoulder-length layers…"
              className="w-full rounded-sm border border-purple-light/20 bg-surface/40 px-4 py-2.5 text-[13px] text-white placeholder-muted focus:border-purple-light focus:outline-none"
            />
          </div>

          <div>
            <label htmlFor="nail" className="mb-1.5 block text-[11px] font-medium text-secondary">
              Nails
            </label>
            <textarea
              id="nail"
              value={nailPreferences}
              onChange={(e) => setNail(e.target.value)}
              rows={3}
              maxLength={2000}
              placeholder="Almond shape, muted pastels, sensitive to acetone…"
              className="w-full rounded-sm border border-purple-light/20 bg-surface/40 px-4 py-2.5 text-[13px] text-white placeholder-muted focus:border-purple-light focus:outline-none"
            />
          </div>
        </Card>

        {/* Style history */}
        {data?.profile?.styleHistory && data.profile.styleHistory.length > 0 && (
          <Card className="lg:col-span-2">
            <h2 className="mb-5 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[2px] text-gold">
              <Sparkles size={12} />
              Style History
            </h2>
            <ul className="flex flex-col gap-3">
              {data.profile.styleHistory.map((h, i) => (
                <li
                  key={i}
                  className="flex items-center justify-between gap-4 border-b border-white/[0.05] pb-3 last:border-0 last:pb-0"
                >
                  <div>
                    <p className="text-[13px] text-white">{h.description}</p>
                    <p className="text-[11px] capitalize text-muted">{h.type}</p>
                  </div>
                  <span className="shrink-0 text-[11px] text-muted">
                    {formatDate(h.date)}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        )}

        <div className="lg:col-span-2">
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
        </div>
      </form>
    </>
  );
}
