'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Calendar,
  Clock,
  User,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Scissors,
  ShieldCheck,
  Check,
  Search,
  CalendarDays,
  ArrowRight,
  Tag,
  Info,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import {
  allServices,
  serviceGroups,
  parsePrice,
  type ServiceGroup,
  type ServiceItem,
} from '@/lib/services';

const timeSlots = [
  {
    period: 'Morning',
    label: 'Morning Hours',
    slots: ['09:00', '10:00', '11:00'],
  },
  {
    period: 'Afternoon',
    label: 'Afternoon Hours',
    slots: ['13:00', '14:00', '15:00', '16:00'],
  },
  {
    period: 'Evening',
    label: 'Evening Hours',
    slots: ['17:00', '18:00', '19:00'],
  },
];

const quickRequestTags = [
  'First time client',
  'Quiet appointment',
  'Sensitive scalp / skin',
  'Consultation before start',
  'Bridal / Event look',
];

function formatSlotLabel(timeStr: string) {
  if (!timeStr) return '';
  const [hourStr, minStr] = timeStr.split(':');
  const hour = parseInt(hourStr, 10);
  if (isNaN(hour)) return timeStr;
  const ampm = hour >= 12 ? 'PM' : 'AM';
  const displayHour = hour % 12 === 0 ? 12 : hour % 12;
  return `${displayHour}:${minStr || '00'} ${ampm}`;
}

function formatFriendlyDate(dateStr: string) {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  if (parts.length !== 3) return dateStr;
  const [y, m, d] = parts.map(Number);
  const obj = new Date(y, m - 1, d);
  return obj.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function getDateShortcut(daysAhead: number): string {
  const d = new Date();
  d.setDate(d.getDate() + daysAhead);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function BookingForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();

  const preselectedGroupParam = searchParams.get('service');
  const mappedGroupId =
    preselectedGroupParam === 'hairstyle' ? 'hair-design' :
    preselectedGroupParam === 'nails' ? 'nail-studio' :
    preselectedGroupParam === 'makeup' ? 'face-laser' :
    preselectedGroupParam;

  const firstGroup = mappedGroupId
    ? serviceGroups.find((g) => g.id === mappedGroupId) || serviceGroups[0]
    : serviceGroups[0];

  const preselectedLook = searchParams.get('look') || '';
  const preselectedServiceName = searchParams.get('serviceName') || '';
  const preselectedNotes = searchParams.get('notes') || '';

  const initialServiceName = () => {
    if (preselectedServiceName) {
      const match = allServices.find(
        (s) => s.name.toLowerCase() === preselectedServiceName.toLowerCase()
      );
      if (match) return match.name;
    }
    return '';
  };

  const initialNotes =
    preselectedNotes || (preselectedLook ? `Requested AI look preview: ${preselectedLook}` : '');

  const [group, setGroup] = useState<ServiceGroup>(firstGroup);
  const [serviceName, setServiceName] = useState(initialServiceName);
  const [searchQuery, setSearchQuery] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [stylistId, setStylistId] = useState('');
  const [notes, setNotes] = useState(initialNotes);

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

  // Filtered services based on group or search query
  const displayedServices = useMemo(() => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return allServices.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.groupLabel.toLowerCase().includes(q) ||
          s.price.toLowerCase().includes(q)
      );
    }
    return allServices.filter((s) => s.groupId === group.id);
  }, [group.id, searchQuery]);

  const selectedServiceObj = useMemo(() => {
    return allServices.find((s) => s.name === serviceName);
  }, [serviceName]);

  const selectedStylistObj = useMemo(() => {
    return stylists.find((s) => s.id === stylistId);
  }, [stylists, stylistId]);

  const minDate = useMemo(() => {
    return new Date().toISOString().split('T')[0];
  }, []);

  const handleToggleNoteTag = (tag: string) => {
    if (notes.includes(tag)) {
      setNotes((prev) => prev.replace(tag, '').replace(/\s{2,}/g, ' ').trim());
    } else {
      setNotes((prev) => (prev ? `${prev}, ${tag}` : tag));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!user) {
      router.push(`/login?redirect=${encodeURIComponent('/booking')}`);
      return;
    }

    if (!serviceName) {
      setError('Please select a service or treatment to proceed.');
      return;
    }

    if (!date || !time) {
      setError('Please select both a date and an appointment time slot.');
      return;
    }

    const appointmentDate = new Date(`${date}T${time}`);
    if (isNaN(appointmentDate.getTime()) || appointmentDate.getTime() < Date.now()) {
      setError('Please choose a valid future date and time for your reservation.');
      return;
    }

    setLoading(true);

    const selectedService = allServices.find((s) => s.name === serviceName);
    const totalPrice = selectedService ? parsePrice(selectedService.price) : null;
    const currentServiceType = selectedService ? selectedService.serviceType : group.serviceType;

    try {
      const res = await fetch('/api/appointments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          serviceName,
          serviceType: currentServiceType,
          appointmentDate: appointmentDate.toISOString(),
          stylistId: stylistId || undefined,
          totalPrice,
          notes: notes.trim() || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? 'Unable to book appointment.');

      setSuccess(true);
      setTimeout(() => router.push('/client/appointments'), 2200);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not book your appointment.');
    } finally {
      setLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-deep">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={32} className="animate-spin text-gold" />
          <p className="text-[13px] tracking-widest text-muted uppercase">Loading Concierge Desk…</p>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6 py-16 bg-deep">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="glass relative max-w-lg rounded-2xl border border-gold/40 p-8 text-center shadow-2xl overflow-hidden"
        >
          {/* Subtle gold ambient glow */}
          <div className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 h-48 w-48 rounded-full bg-gold/15 blur-3xl" />

          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-gold/15 border border-gold/40 text-gold shadow-lg">
            <CheckCircle2 size={36} />
          </div>

          <span className="inline-block rounded-full border border-gold/30 bg-gold/10 px-3.5 py-1 text-[11px] font-semibold uppercase tracking-[2px] text-gold mb-3">
            ✦ Reservation Confirmed ✦
          </span>

          <h2 className="mb-2 font-serif text-3xl text-white">Your Treatment is Booked</h2>
          <p className="mb-6 text-[14px] text-secondary leading-relaxed">
            We have reserved your appointment with Andrea&apos;s Aesthetic & Wellness Clinic.
            A confirmation has been saved to your client portfolio.
          </p>

          <div className="rounded-xl border border-purple-light/20 bg-surface/40 p-4 text-left text-[13px] space-y-2 mb-6">
            <div className="flex justify-between">
              <span className="text-muted">Treatment:</span>
              <span className="font-medium text-white">{serviceName}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Schedule:</span>
              <span className="font-medium text-gold">
                {formatFriendlyDate(date)} at {formatSlotLabel(time)}
              </span>
            </div>
            {selectedStylistObj && (
              <div className="flex justify-between">
                <span className="text-muted">Specialist:</span>
                <span className="font-medium text-white">{selectedStylistObj.name}</span>
              </div>
            )}
            {preselectedLook && (
              <div className="flex justify-between">
                <span className="text-muted">AI Look:</span>
                <span className="font-medium text-gold">✦ {preselectedLook}</span>
              </div>
            )}
          </div>

          <div className="flex items-center justify-center gap-2 text-[12px] text-muted">
            <Loader2 size={14} className="animate-spin text-gold" />
            <span>Redirecting to your appointments dashboard…</span>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-deep px-4 py-10 sm:px-6 lg:px-12">
      <div className="mx-auto max-w-7xl">
        {/* Page Top Header */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 text-center md:text-left"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-gold/30 bg-gold/10 px-3.5 py-1 text-[10px] font-semibold uppercase tracking-[2px] text-gold mb-3">
            <Sparkles size={12} className="text-gold" />
            <span>Andrea&apos;s Clinic Concierge</span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-white tracking-tight">
            Reserve Your Experience
          </h1>
          <p className="mt-2 max-w-2xl text-[14px] text-secondary">
            Select your signature treatment, preferred time, and dedicated specialist. Experience
            transformative aesthetic care in Daet.
          </p>
        </motion.div>

        {/* Global Error Banner */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-6 flex items-start gap-3 rounded-xl border border-error/40 bg-error/15 p-4 text-[13px] text-white shadow-lg"
            >
              <AlertCircle size={18} className="mt-0.5 shrink-0 text-error" />
              <div className="flex-1">
                <p className="font-medium text-error">Reservation Incomplete</p>
                <p className="mt-0.5 text-secondary">{error}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* AI Look Spotlight Banner */}
        {preselectedLook && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 relative overflow-hidden rounded-2xl border border-gold/50 bg-gradient-to-r from-card via-surface/80 to-card p-5 sm:p-6 shadow-xl"
          >
            <div className="pointer-events-none absolute -right-10 -top-10 h-36 w-36 rounded-full bg-gold/15 blur-2xl" />
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 relative z-10">
              <div className="flex items-start gap-3.5">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-gold/40 bg-gold/15 text-gold shadow-md">
                  <Sparkles size={20} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-[1.5px] text-gold">
                      AI Studio Look Pre-Selected
                    </span>
                    <span className="h-1.5 w-1.5 rounded-full bg-gold animate-pulse" />
                  </div>
                  <h3 className="font-serif text-xl sm:text-2xl text-white mt-0.5">
                    Styling for: <span className="text-gold italic font-sans font-semibold">{preselectedLook}</span>
                  </h3>
                  <p className="text-[12px] sm:text-[13px] text-secondary mt-1">
                    Your generated visual reference has been linked to this appointment. Our stylists will tailor the service directly to your virtual look.
                  </p>
                </div>
              </div>
              <div className="self-stretch sm:self-auto flex items-center justify-center rounded-xl border border-gold/30 bg-gold/10 px-4 py-2 text-[12px] text-gold font-medium">
                ✦ Preview Synced
              </div>
            </div>
          </motion.div>
        )}

        {/* 2-Column Responsive Layout */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 items-start">
          {/* Main Booking Form Column */}
          <div className="lg:col-span-8 space-y-8">
            {/* Step 1: Treatment Category & Service Selection */}
            <section className="glass rounded-2xl border border-purple-light/20 p-6 sm:p-7 shadow-xl">
              <div className="mb-6 flex flex-wrap items-center justify-between gap-2 border-b border-purple-light/15 pb-4">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gold/20 text-[12px] font-bold text-gold border border-gold/40">
                    1
                  </span>
                  <h2 className="font-serif text-xl text-white">Select Your Treatment</h2>
                </div>
                {selectedServiceObj && (
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-gold/30 bg-gold/10 px-3 py-0.5 text-[11px] font-medium text-gold">
                    <Check size={12} />
                    {selectedServiceObj.name}
                  </span>
                )}
              </div>

              {/* Category selector pills */}
              <div className="mb-6">
                <label className="mb-2.5 block text-[11px] font-semibold uppercase tracking-[1px] text-muted">
                  Treatment Category
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  {serviceGroups.map((g) => {
                    const isActive = group.id === g.id && !searchQuery.trim();
                    return (
                      <button
                        key={g.id}
                        type="button"
                        onClick={() => {
                          setGroup(g);
                          setSearchQuery('');
                        }}
                        className={`group relative flex flex-col items-start rounded-xl border p-3.5 text-left transition-all duration-200 ${
                          isActive
                            ? 'border-gold bg-gold/10 shadow-lg shadow-gold/5 ring-1 ring-gold'
                            : 'border-purple-light/15 bg-card/60 text-secondary hover:border-purple-light/40 hover:bg-surface/30'
                        }`}
                      >
                        <span
                          className={`text-[13px] font-semibold transition-colors ${
                            isActive ? 'text-gold' : 'text-white group-hover:text-gold-hover'
                          }`}
                        >
                          {g.label}
                        </span>
                        <span className="mt-1 line-clamp-1 text-[11px] text-muted">
                          {g.sub}
                        </span>
                        {isActive && (
                          <div className="absolute top-2 right-2 h-2 w-2 rounded-full bg-gold" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Instant Search Bar */}
              <div className="mb-4">
                <div className="relative">
                  <Search
                    size={16}
                    className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted"
                  />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search any service (e.g. HydraFacial, Balayage, Gel Manicure, Head Spa)..."
                    className="w-full rounded-xl border border-purple-light/20 bg-surface/40 py-2.5 pl-10 pr-4 text-[13px] text-white placeholder-muted focus:border-gold focus:outline-none focus:ring-1 focus:ring-gold transition-all"
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] text-muted hover:text-white"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              {/* Service Cards Grid */}
              <div>
                <div className="mb-2.5 flex items-center justify-between">
                  <label className="text-[11px] font-semibold uppercase tracking-[1px] text-muted">
                    {searchQuery ? `Search Results (${displayedServices.length})` : `${group.label} Services`}
                  </label>
                  <span className="text-[11px] text-muted">Tap to select</span>
                </div>

                <div className="max-h-[340px] overflow-y-auto scrollbar-thin pr-1 space-y-2">
                  {displayedServices.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-purple-light/20 p-6 text-center text-muted">
                      <p className="text-[13px]">No treatments match your search.</p>
                      <button
                        type="button"
                        onClick={() => setSearchQuery('')}
                        className="mt-2 text-[12px] text-gold underline underline-offset-4"
                      >
                        Reset search
                      </button>
                    </div>
                  ) : (
                    displayedServices.map((s) => {
                      const isSelected = serviceName === s.name;
                      return (
                        <div
                          key={s.name}
                          onClick={() => setServiceName(s.name)}
                          className={`group flex cursor-pointer items-center justify-between rounded-xl border p-3.5 transition-all duration-200 ${
                            isSelected
                              ? 'border-gold bg-gold/15 shadow-md shadow-gold/5 ring-1 ring-gold'
                              : 'border-purple-light/15 bg-card/40 hover:border-purple-light/40 hover:bg-surface/30'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div
                              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors ${
                                isSelected
                                  ? 'border-gold bg-gold text-card'
                                  : 'border-purple-light/30 group-hover:border-purple-light'
                              }`}
                            >
                              {isSelected && <Check size={12} strokeWidth={3} />}
                            </div>
                            <div>
                              <p
                                className={`text-[13px] font-medium transition-colors ${
                                  isSelected ? 'text-white' : 'text-secondary group-hover:text-white'
                                }`}
                              >
                                {s.name}
                              </p>
                              <p className="text-[11px] text-muted">{s.groupLabel}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <span
                              className={`inline-block rounded-md px-2.5 py-1 text-[12px] font-semibold transition-colors ${
                                isSelected
                                  ? 'bg-gold text-card'
                                  : 'border border-gold/30 bg-gold/5 text-gold'
                              }`}
                            >
                              {s.price}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </section>

            {/* Step 2: Date & Curated Time Slot Picker */}
            <section className="glass rounded-2xl border border-purple-light/20 p-6 sm:p-7 shadow-xl">
              <div className="mb-6 flex flex-wrap items-center justify-between gap-2 border-b border-purple-light/15 pb-4">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gold/20 text-[12px] font-bold text-gold border border-gold/40">
                    2
                  </span>
                  <h2 className="font-serif text-xl text-white">Choose Date & Time</h2>
                </div>
                {date && time && (
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-gold/30 bg-gold/10 px-3 py-0.5 text-[11px] font-medium text-gold">
                    <CalendarDays size={12} />
                    {formatFriendlyDate(date)} • {formatSlotLabel(time)}
                  </span>
                )}
              </div>

              {/* Date Selection */}
              <div className="mb-6">
                <div className="mb-2 flex items-center justify-between">
                  <label htmlFor="date" className="text-[11px] font-semibold uppercase tracking-[1px] text-muted">
                    Appointment Date
                  </label>
                  <span className="text-[11px] text-muted">Quick select:</span>
                </div>

                {/* Quick Date Shortcuts */}
                <div className="mb-3 flex flex-wrap gap-2">
                  {[
                    { label: 'Today', offset: 0 },
                    { label: 'Tomorrow', offset: 1 },
                    { label: 'In 2 Days', offset: 2 },
                    { label: 'Next Weekend', offset: 5 },
                  ].map((s) => {
                    const target = getDateShortcut(s.offset);
                    const isSelected = date === target;
                    return (
                      <button
                        key={s.label}
                        type="button"
                        onClick={() => setDate(target)}
                        className={`rounded-lg border px-3 py-1.5 text-[11px] font-medium transition-all ${
                          isSelected
                            ? 'border-gold bg-gold text-card font-semibold'
                            : 'border-purple-light/20 bg-card/60 text-secondary hover:border-purple-light/40'
                        }`}
                      >
                        {s.label}
                      </button>
                    );
                  })}
                </div>

                <div className="relative">
                  <Calendar
                    size={16}
                    className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-gold"
                  />
                  <input
                    id="date"
                    type="date"
                    value={date}
                    min={minDate}
                    onChange={(e) => setDate(e.target.value)}
                    required
                    className="w-full rounded-xl border border-purple-light/20 bg-surface/40 py-2.5 pl-10 pr-4 text-[13px] text-white focus:border-gold focus:outline-none focus:ring-1 focus:ring-gold transition-all"
                  />
                </div>
              </div>

              {/* Curated Interactive Time Slots */}
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <label className="text-[11px] font-semibold uppercase tracking-[1px] text-muted">
                    Curated Time Slots
                  </label>
                  <span className="text-[11px] text-muted"> Daet Clinic Hours: 9 AM - 7 PM</span>
                </div>

                <div className="space-y-3.5">
                  {timeSlots.map((cat) => (
                    <div key={cat.period} className="rounded-xl border border-purple-light/10 bg-card/30 p-3">
                      <p className="mb-2 text-[11px] font-medium text-muted">{cat.label}</p>
                      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                        {cat.slots.map((slot) => {
                          const isSlotSelected = time === slot;
                          return (
                            <button
                              key={slot}
                              type="button"
                              onClick={() => setTime(slot)}
                              className={`flex items-center justify-center gap-1.5 rounded-lg border py-2 text-[12px] font-medium transition-all ${
                                isSlotSelected
                                  ? 'border-gold bg-gold text-card font-bold shadow-md shadow-gold/10'
                                  : 'border-purple-light/15 bg-surface/30 text-secondary hover:border-gold/50 hover:bg-surface/60'
                              }`}
                            >
                              <Clock size={12} className={isSlotSelected ? 'text-card' : 'text-gold'} />
                              <span>{formatSlotLabel(slot)}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Custom Time Option */}
                <div className="mt-3 flex items-center gap-3">
                  <label htmlFor="customTime" className="text-[11px] text-muted shrink-0">
                    Or custom time:
                  </label>
                  <input
                    id="customTime"
                    type="time"
                    value={time}
                    onChange={(e) => setTime(e.target.value)}
                    className="rounded-lg border border-purple-light/20 bg-surface/40 px-3 py-1.5 text-[12px] text-white focus:border-gold focus:outline-none"
                  />
                </div>
              </div>
            </section>

            {/* Step 3: Dedicated Stylist / Specialist Choice */}
            <section className="glass rounded-2xl border border-purple-light/20 p-6 sm:p-7 shadow-xl">
              <div className="mb-6 flex flex-wrap items-center justify-between gap-2 border-b border-purple-light/15 pb-4">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gold/20 text-[12px] font-bold text-gold border border-gold/40">
                    3
                  </span>
                  <h2 className="font-serif text-xl text-white">Specialist Preference</h2>
                </div>
                <span className="text-[11px] text-muted">Optional</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {/* Any Specialist Option */}
                <div
                  onClick={() => setStylistId('')}
                  className={`cursor-pointer rounded-xl border p-4 transition-all duration-200 ${
                    stylistId === ''
                      ? 'border-gold bg-gold/15 shadow-md shadow-gold/5 ring-1 ring-gold'
                      : 'border-purple-light/15 bg-card/40 hover:border-purple-light/40 hover:bg-surface/30'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border ${
                        stylistId === ''
                          ? 'border-gold bg-gold text-card'
                          : 'border-purple-light/30 bg-surface/60 text-gold'
                      }`}
                    >
                      <Sparkles size={18} />
                    </div>
                    <div>
                      <p className="text-[13px] font-semibold text-white">First Available</p>
                      <p className="text-[11px] text-muted">Fastest schedule</p>
                    </div>
                  </div>
                </div>

                {/* Stylist Cards */}
                {stylists.map((st) => {
                  const isSelected = stylistId === st.id;
                  const initials = st.name
                    .split(' ')
                    .map((n) => n[0])
                    .slice(0, 2)
                    .join('')
                    .toUpperCase();
                  return (
                    <div
                      key={st.id}
                      onClick={() => setStylistId(st.id)}
                      className={`cursor-pointer rounded-xl border p-4 transition-all duration-200 ${
                        isSelected
                          ? 'border-gold bg-gold/15 shadow-md shadow-gold/5 ring-1 ring-gold'
                          : 'border-purple-light/15 bg-card/40 hover:border-purple-light/40 hover:bg-surface/30'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border text-[12px] font-bold ${
                            isSelected
                              ? 'border-gold bg-gold text-card'
                              : 'border-purple-light/30 bg-surface/60 text-secondary'
                          }`}
                        >
                          {initials}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-[13px] font-semibold text-white">{st.name}</p>
                          <p className="text-[11px] text-gold">Certified Specialist</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Step 4: Notes & Personalized Requests */}
            <section className="glass rounded-2xl border border-purple-light/20 p-6 sm:p-7 shadow-xl">
              <div className="mb-4 flex items-center justify-between border-b border-purple-light/15 pb-4">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gold/20 text-[12px] font-bold text-gold border border-gold/40">
                    4
                  </span>
                  <h2 className="font-serif text-xl text-white">Consultation & Preferences</h2>
                </div>
                <span className="text-[11px] text-muted">Optional</span>
              </div>

              <div className="mb-3">
                <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[1px] text-muted">
                  Quick Preference Add-ons
                </label>
                <div className="flex flex-wrap gap-2">
                  {quickRequestTags.map((tag) => {
                    const hasTag = notes.includes(tag);
                    return (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => handleToggleNoteTag(tag)}
                        className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[11px] font-medium transition-all ${
                          hasTag
                            ? 'border-gold bg-gold/15 text-gold font-semibold'
                            : 'border-purple-light/20 bg-card/40 text-muted hover:border-purple-light/40 hover:text-secondary'
                        }`}
                      >
                        <Tag size={11} className={hasTag ? 'text-gold' : 'text-muted'} />
                        <span>{tag}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label htmlFor="notes" className="mb-2 block text-[11px] font-semibold uppercase tracking-[1px] text-muted">
                  Special Instructions / Allergies / Notes
                </label>
                <textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  maxLength={1000}
                  className="w-full rounded-xl border border-purple-light/20 bg-surface/40 p-3.5 text-[13px] text-white placeholder-muted focus:border-gold focus:outline-none focus:ring-1 focus:ring-gold transition-all"
                  placeholder="Tell us about allergies, preferred hair thickness/length, skin sensitivities, or reference details…"
                />
              </div>
            </section>
          </div>

          {/* Sticky Reservation Summary Desk (Right Column) */}
          <div className="lg:col-span-4 lg:sticky lg:top-24">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass relative rounded-2xl border border-gold/30 p-6 sm:p-7 shadow-2xl overflow-hidden"
            >
              {/* Subtle gold glow */}
              <div className="pointer-events-none absolute -top-16 -right-16 h-36 w-36 rounded-full bg-gold/15 blur-2xl" />

              <div className="mb-6 flex items-center justify-between border-b border-gold/20 pb-4">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-[2px] text-gold">
                    ✦ Desk Concierge ✦
                  </span>
                  <h3 className="font-serif text-2xl text-white mt-0.5">Booking Summary</h3>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-full border border-gold/40 bg-gold/10 text-gold">
                  <Sparkles size={16} />
                </div>
              </div>

              {/* Summary Items */}
              <div className="space-y-4 mb-6">
                {/* Service */}
                <div className="flex items-start justify-between gap-3 text-[13px]">
                  <div className="flex items-center gap-2 text-muted">
                    <Scissors size={14} className="text-gold shrink-0" />
                    <span>Treatment:</span>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-white">
                      {serviceName || <span className="text-muted italic">None selected</span>}
                    </p>
                    {selectedServiceObj && (
                      <p className="text-[11px] text-gold">{selectedServiceObj.groupLabel}</p>
                    )}
                  </div>
                </div>

                {/* Date */}
                <div className="flex items-center justify-between text-[13px]">
                  <div className="flex items-center gap-2 text-muted">
                    <Calendar size={14} className="text-gold shrink-0" />
                    <span>Date:</span>
                  </div>
                  <p className="font-medium text-white">
                    {date ? formatFriendlyDate(date) : <span className="text-muted italic">Choose date</span>}
                  </p>
                </div>

                {/* Time */}
                <div className="flex items-center justify-between text-[13px]">
                  <div className="flex items-center gap-2 text-muted">
                    <Clock size={14} className="text-gold shrink-0" />
                    <span>Time:</span>
                  </div>
                  <p className="font-medium text-white">
                    {time ? formatSlotLabel(time) : <span className="text-muted italic">Choose slot</span>}
                  </p>
                </div>

                {/* Stylist */}
                <div className="flex items-center justify-between text-[13px]">
                  <div className="flex items-center gap-2 text-muted">
                    <User size={14} className="text-gold shrink-0" />
                    <span>Specialist:</span>
                  </div>
                  <p className="font-medium text-white">
                    {selectedStylistObj ? selectedStylistObj.name : 'First Available'}
                  </p>
                </div>

                {/* AI Look indicator */}
                {preselectedLook && (
                  <div className="flex items-center justify-between rounded-lg border border-gold/30 bg-gold/10 px-3 py-2 text-[12px]">
                    <div className="flex items-center gap-1.5 text-gold">
                      <Sparkles size={13} />
                      <span className="font-semibold">AI Look:</span>
                    </div>
                    <span className="font-medium text-white">{preselectedLook}</span>
                  </div>
                )}
              </div>

              {/* Price Breakdown */}
              <div className="rounded-xl border border-purple-light/20 bg-surface/50 p-4 mb-6">
                <div className="flex items-baseline justify-between">
                  <div>
                    <span className="text-[11px] font-semibold uppercase tracking-[1px] text-muted">
                      Estimated Total
                    </span>
                    <p className="text-[11px] text-secondary mt-0.5">Pay at clinic after service</p>
                  </div>
                  <div className="text-right">
                    <span className="font-serif text-2xl font-bold text-gold">
                      {selectedServiceObj ? selectedServiceObj.price : '—'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Submit CTA */}
              <button
                type="button"
                onClick={handleSubmit}
                disabled={loading}
                className="group relative flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-gold via-gold-hover to-gold px-6 py-3.5 text-[12px] font-bold uppercase tracking-[2px] text-card shadow-lg shadow-gold/20 transition-all hover:scale-[1.01] hover:shadow-gold/30 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 size={16} className="animate-spin text-card" />
                    <span>Confirming Reservation…</span>
                  </>
                ) : (
                  <>
                    <span>Confirm Reservation</span>
                    <ArrowRight
                      size={15}
                      className="transition-transform duration-200 group-hover:translate-x-1"
                    />
                  </>
                )}
              </button>

              {!user && (
                <p className="mt-3 text-center text-[11px] text-muted">
                  You&apos;ll be directed to sign in to finalize your booking.
                </p>
              )}

              {/* Trust & Guarantee Badges */}
              <div className="mt-6 pt-5 border-t border-purple-light/15 space-y-2.5 text-[11px] text-secondary">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={14} className="text-gold shrink-0" />
                  <span>Complimentary consultation included</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 size={14} className="text-gold shrink-0" />
                  <span>Free cancellation up to 2 hours prior</span>
                </div>
                <div className="flex items-center gap-2">
                  <Sparkles size={14} className="text-gold shrink-0" />
                  <span>Authentic salon experience in Daet, Camarines Norte</span>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}
