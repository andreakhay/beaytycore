import Link from 'next/link';
import { MapPin, Mail, Clock } from 'lucide-react';

const columns = [
  {
    icon: MapPin,
    title: 'Location',
    lines: ['Purok 5, Bagasbas Road', 'Daet, Camarines Norte 4600', 'Philippines'],
  },
  {
    icon: Mail,
    title: 'Contact',
    lines: ['andreasaestheticwellness@gmail.com', '+63 954 123 4567'],
  },
  {
    icon: Clock,
    title: 'Hours',
    lines: ['Mon–Sat: 9AM – 8PM', 'Sunday: 10AM – 6PM'],
  },
];

export default function Footer() {
  return (
    <footer className="border-t border-purple-light/15 bg-gradient-to-b from-card to-deep px-6 pt-16 lg:px-10">
      {/* Wordmark */}
      <div className="mb-12 flex flex-col items-center">
        <span className="font-serif text-lg font-semibold tracking-[3px] text-white">
          ANDREA&apos;S
        </span>
        <span className="text-[8px] uppercase tracking-[2px] text-gold">
          Aesthetic &amp; Wellness Clinic
        </span>
      </div>

      {/* Detail columns */}
      <div className="mx-auto mb-12 grid max-w-4xl grid-cols-1 gap-8 text-center sm:grid-cols-3">
        {columns.map(({ icon: Icon, title, lines }) => (
          <div key={title}>
            <h4 className="mb-3.5 flex items-center justify-center gap-2 text-[10px] font-semibold uppercase tracking-[2.5px] text-gold">
              <Icon size={12} />
              {title}
            </h4>
            <p className="text-xs leading-[1.9] text-secondary">
              {lines.map((line, i) => (
                <span key={i}>
                  {line}
                  {i < lines.length - 1 && <br />}
                </span>
              ))}
            </p>
          </div>
        ))}
      </div>

      {/* Bottom bar */}
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-3 border-t border-white/[0.07] py-5 text-center sm:flex-row sm:justify-between sm:text-left">
        <p className="text-[10px] tracking-[0.5px] text-muted">
          © {new Date().getFullYear()} Andrea&apos;s Aesthetic &amp; Wellness Clinic. All rights reserved.
        </p>
        <div className="flex gap-5">
          {[
            { href: '/contact', label: 'Contact' },
            { href: '/services', label: 'Services' },
            { href: '/about', label: 'About' },
          ].map((l) => (
            <Link
              key={l.label}
              href={l.href}
              className="text-[10px] tracking-[0.5px] text-muted transition-colors hover:text-gold"
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </footer>
  );
}
