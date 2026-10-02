import type { Metadata } from 'next';
import { MapPin, Mail, Phone, Clock, Send } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Contact',
  description:
    "Visit Andrea's Aesthetic & Wellness Clinic in Daet, Camarines Norte. Open Monday to Saturday 9AM–8PM, Sunday 10AM–6PM.",
};

const details = [
  {
    icon: MapPin,
    label: 'Address',
    lines: ['Purok 5, Bagasbas Road', 'Daet, Camarines Norte 4600', 'Philippines'],
  },
  {
    icon: Mail,
    label: 'Email',
    lines: ['andreasaestheticwellness@gmail.com'],
    href: 'mailto:andreasaestheticwellness@gmail.com',
  },
  {
    icon: Phone,
    label: 'Phone',
    lines: ['+63 954 123 4567'],
    href: 'tel:+639541234567',
  },
];

const hours = [
  { day: 'Monday – Friday', time: '9:00 AM – 8:00 PM' },
  { day: 'Saturday', time: '9:00 AM – 8:00 PM' },
  { day: 'Sunday', time: '10:00 AM – 6:00 PM' },
];

export default function ContactPage() {
  return (
    <>
      {/* Header */}
      <section className="relative overflow-hidden border-b border-purple-light/15 px-6 py-20 lg:px-10">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-purple/20 blur-[110px]"
        />
        <div className="relative mx-auto max-w-7xl">
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-[3px] text-gold">
            Get in touch
          </p>
          <h1 className="mb-4 font-serif text-5xl text-white sm:text-6xl">Visit us</h1>
          <p className="max-w-xl text-[15px] leading-relaxed text-secondary">
            Walk-ins are welcome, though booking ahead means you won&apos;t wait.
          </p>
        </div>
      </section>

      <section className="px-6 py-16 lg:px-10">
        <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-3">
          {/* Contact details */}
          <div className="flex flex-col gap-6 lg:col-span-2">
            <div className="grid gap-6 sm:grid-cols-3">
              {details.map((d) => (
                <div
                  key={d.label}
                  className="rounded-sm border border-purple-light/15 bg-card p-6"
                >
                  <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-full border border-gold/30 bg-gold/10">
                    <d.icon size={16} className="text-gold" />
                  </div>
                  <h3 className="mb-2.5 text-[10px] font-semibold uppercase tracking-[2px] text-gold">
                    {d.label}
                  </h3>
                  {d.href ? (
                    <a
                      href={d.href}
                      className="break-words text-[13px] leading-relaxed text-secondary transition-colors hover:text-white"
                    >
                      {d.lines.join(' ')}
                    </a>
                  ) : (
                    <p className="text-[13px] leading-relaxed text-secondary">
                      {d.lines.map((l, i) => (
                        <span key={i}>
                          {l}
                          {i < d.lines.length - 1 && <br />}
                        </span>
                      ))}
                    </p>
                  )}
                </div>
              ))}
            </div>

            {/* Map */}
            <div className="overflow-hidden rounded-sm border border-purple-light/15">
              <iframe
                title="Map showing Andrea's Aesthetic & Wellness Clinic in Daet, Camarines Norte"
                src="https://www.google.com/maps?q=Bagasbas+Road,+Daet,+Camarines+Norte&output=embed"
                width="100%"
                height="360"
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                className="block border-0 grayscale-[35%]"
              />
            </div>
          </div>

          {/* Hours + socials */}
          <div className="flex flex-col gap-6">
            <div className="rounded-sm border border-purple-light/15 bg-card p-6">
              <h3 className="mb-5 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[2px] text-gold">
                <Clock size={13} />
                Opening Hours
              </h3>
              <ul className="flex flex-col gap-3">
                {hours.map((h) => (
                  <li
                    key={h.day}
                    className="flex items-baseline justify-between gap-3 border-b border-white/[0.04] pb-3 last:border-0 last:pb-0"
                  >
                    <span className="text-[13px] text-secondary">{h.day}</span>
                    <span className="shrink-0 text-[13px] font-medium text-white">
                      {h.time}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-sm border border-purple-light/15 bg-card p-6">
              <h3 className="mb-4 text-[10px] font-semibold uppercase tracking-[2px] text-gold">
                Message Us
              </h3>
              <p className="mb-4 text-[12px] leading-relaxed text-muted">
                For the fastest reply, email us or call during opening hours.
              </p>
              <a
                href="mailto:andreasaestheticwellness@gmail.com"
                className="flex items-center justify-center gap-2 border border-purple-light/40 px-5 py-2.5 text-[11px] font-semibold uppercase tracking-[1.5px] text-secondary transition-colors hover:border-gold/50 hover:text-gold"
              >
                <Send size={13} />
                Send an Email
              </a>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
