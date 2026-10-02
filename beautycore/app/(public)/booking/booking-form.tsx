'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Calendar, Clock, User, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { allServices, serviceGroups, parsePrice, type ServiceGroup } from '@/lib/services';

export default function BookingForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();

  const preselectedGroup = searchParams.get('service');
  const firstGroup = preselectedGroup
    ? serviceGroups.find((g) => g.id === preselectedGroup) || serviceGroups[0]
    : serviceGroups[0];

  const [group, setGroup] = useState<ServiceGroup>(firstGroup);
  const [serviceName, setServiceName] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [stylistId, setStylistId] = useState('');
  const [notes, setNotes] = useState('');

  const [stylists, setStylists] = useState<Array<{ id: string; name: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    fetch('/api/stylists')
      .then((r) => r.json())
      .then((data) => setStylists(data.stylists || []))
      .catch(() => setStylists([]));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!user) {
      router.push(`/login?redirect=${encodeURIComponent('/booking')}`);
      return;
    }

    if (!date || !time) {
      setError('Please select a date and time.');
      setLoading(false);
      return;
    }

    const appointmentDate = new Date(`${date}T${time}`);
    if (appointmentDate.getTime() < Date.now()) {
      setError('Please choose a future date and time.');
      setLoading(false);
      return;
    }

    const selectedService = allServices.find((s) => s.name === serviceName);
    const totalPrice = selectedService ? parsePrice(selectedService.price) : null;

    try {
      const res = await fetch('/api/appointments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          serviceName,
          serviceType: group.serviceType,
          appointmentDate: appointmentDate.toISOString(),
          stylistId: stylistId || undefined,
          totalPrice,
          notes: notes.trim() || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? 'Unable to book appointment.');

      setSuccess(true);
      setTimeout(() => router.push('/client/appointments'), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not book your appointment.');
    } finally {
      setLoading(false);
    }
  };

  const serviceOptions = allServices
    .filter((s) => s.groupId === group.id)
    .map((s) => ({ value: s.name, label: `${s.name} — ${s.price}` }));

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 size={24} className="animate-spin text-gold" />
      </div>
    );
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <CheckCircle size={48} className="mx-auto mb-4 text-success" />
          <h2 className="mb-2 font-serif text-3xl text-white">Appointment booked</h2>
          <p className="text-muted">Redirecting you to your appointments…</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-6 py-12 lg:px-10">
      <div className="mx-auto max-w-2xl">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="mb-2 font-serif text-4xl text-white">Book an Appointment</h1>
          <p className="mb-8 text-[14px] text-secondary">
            Pick a service, choose a time, and we&apos;ll see you soon.
          </p>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 flex items-start gap-2 rounded-sm border border-error/30 bg-error/10 p-4 text-[13px] text-error"
            >
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="glass rounded-sm p-6">
            {/* Category */}
            <div className="mb-5">
              <label className="mb-2 block text-[11px] font-medium text-secondary">
                Service Category
              </label>
              <div className="grid gap-2 sm:grid-cols-2">
                {serviceGroups.map((g) => (
                  <button
                    key={g.id}
                    type="button"
                    onClick={() => {
                      setGroup(g);
                      setServiceName('');
                    }}
                    className={`rounded-sm border px-4 py-2.5 text-left text-[13px] transition-colors ${
                      group.id === g.id
                        ? 'border-gold/40 bg-gold/10 text-white'
                        : 'border-purple-light/15 text-muted hover:border-purple-light/40'
                    }`}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Service */}
            <div className="mb-5">
              <label htmlFor="service" className="mb-2 block text-[11px] font-medium text-secondary">
                Service
              </label>
              <select
                id="service"
                value={serviceName}
                onChange={(e) => setServiceName(e.target.value)}
                required
                className="w-full rounded-sm border border-purple-light/20 bg-surface/40 px-4 py-2.5 text-[13px] text-white focus:border-purple-light focus:outline-none"
              >
                <option value="">Choose a service</option>
                {serviceOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Date */}
            <div className="mb-5 grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="date" className="mb-2 block text-[11px] font-medium text-secondary">
                  <Calendar size={13} className="mr-1 inline" />
                  Date
                </label>
                <input
                  id="date"
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                  required
                  className="w-full rounded-sm border border-purple-light/20 bg-surface/40 px-4 py-2.5 text-[13px] text-white focus:border-purple-light focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="time" className="mb-2 block text-[11px] font-medium text-secondary">
                  <Clock size={13} className="mr-1 inline" />
                  Time
                </label>
                <input
                  id="time"
                  type="time"
                  value={time}
                  onChange={(e) => setTime(e.target.value)}
                  required
                  className="w-full rounded-sm border border-purple-light/20 bg-surface/40 px-4 py-2.5 text-[13px] text-white focus:border-purple-light focus:outline-none"
                />
              </div>
            </div>

            {/* Stylist */}
            <div className="mb-5">
              <label htmlFor="stylist" className="mb-2 block text-[11px] font-medium text-secondary">
                <User size={13} className="mr-1 inline" />
                Preferred Stylist (optional)
              </label>
              <select
                id="stylist"
                value={stylistId}
                onChange={(e) => setStylistId(e.target.value)}
                className="w-full rounded-sm border border-purple-light/20 bg-surface/40 px-4 py-2.5 text-[13px] text-white focus:border-purple-light focus:outline-none"
              >
                <option value="">No preference</option>
                {stylists.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Notes */}
            <div className="mb-6">
              <label htmlFor="notes" className="mb-2 block text-[11px] font-medium text-secondary">
                Special Requests (optional)
              </label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                maxLength={1000}
                className="w-full rounded-sm border border-purple-light/20 bg-surface/40 px-4 py-2.5 text-[13px] text-white placeholder-muted focus:border-purple-light focus:outline-none"
                placeholder="Allergies, preferences, or anything we should know…"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 bg-gold px-6 py-3 text-[11px] font-semibold uppercase tracking-[2px] text-card transition-all hover:bg-gold-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Booking…
                </>
              ) : (
                'Confirm Booking'
              )}
            </button>

            {!user && (
              <p className="mt-4 text-center text-[12px] text-muted">
                You&apos;ll be asked to sign in before confirming.
              </p>
            )}
          </form>
        </motion.div>
      </div>
    </div>
  );
}
