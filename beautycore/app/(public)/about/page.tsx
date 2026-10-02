import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import { Award, Heart, Sparkles, Users } from 'lucide-react';

export const metadata: Metadata = {
  title: 'About',
  description:
    "Andrea's Aesthetic & Wellness Clinic — over 15 years of aesthetic medicine and holistic wellness in Daet, Camarines Norte.",
};

const values = [
  {
    icon: Heart,
    title: 'Care first',
    body: 'We say no when a treatment is wrong for your hair or skin, even when it is what you came in asking for.',
  },
  {
    icon: Award,
    title: 'Certified specialists',
    body: 'Facials and laser work are performed only by certified aesthetic practitioners — never delegated.',
  },
  {
    icon: Sparkles,
    title: 'Honest guidance',
    body: 'Our AI advisor and our stylists tell you what is realistically achievable from where your hair is today.',
  },
  {
    icon: Users,
    title: 'One roof',
    body: 'Hair, nails, skin, and massage in a single visit, coordinated by people who talk to each other.',
  },
];

export default function AboutPage() {
  return (
    <>
      {/* Header */}
      <section className="relative overflow-hidden border-b border-purple-light/15 px-6 py-20 lg:px-10">
        <div
          aria-hidden
          className="pointer-events-none absolute -left-24 -top-24 h-96 w-96 rounded-full bg-purple/20 blur-[110px]"
        />
        <div className="relative mx-auto max-w-7xl">
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-[3px] text-gold">
            About Us
          </p>
          <h1 className="mb-4 font-serif text-5xl text-white sm:text-6xl">
            A sanctuary in Daet
          </h1>
          <p className="max-w-xl text-[15px] leading-relaxed text-secondary">
            Where beauty and wellness converge — and where nobody rushes you
            through a treatment to make the next booking.
          </p>
        </div>
      </section>

      {/* Founder */}
      <section className="px-6 py-20 lg:px-10">
        <div className="mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-2">
          <div className="relative aspect-[4/5] overflow-hidden rounded-sm border border-purple-light/20">
            <Image
              src="/aboutpic.jpg"
              alt="Inside Andrea's Aesthetic & Wellness Clinic"
              fill
              sizes="(max-width: 1024px) 100vw, 50vw"
              className="object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-deep/60 via-transparent to-transparent" />
          </div>

          <div>
            <p className="mb-3 text-[10px] font-semibold uppercase tracking-[3px] text-gold">
              Our Founder
            </p>
            <h2 className="mb-6 font-serif text-4xl text-white">Andrea</h2>
            <div className="flex flex-col gap-4 text-[14px] leading-relaxed text-secondary">
              <p>
                Andrea founded this clinic with a singular vision: to create a
                sanctuary where beauty and wellness converge. With over 15 years
                of experience in aesthetic medicine and holistic wellness, she
                built a practice around a simple conviction — that looking after
                yourself should never feel transactional.
              </p>
              <p>
                That conviction shapes how the clinic runs. Consultations are
                unhurried. Treatments are recommended on merit, not margin. And
                the team is trained to read what your hair and skin actually
                need before reaching for a product.
              </p>
              <p className="font-serif text-lg italic text-gold">
                &ldquo;Self-care is not an indulgence. It&apos;s a necessity.&rdquo;
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="border-y border-purple-light/15 bg-card px-6 py-20 lg:px-10">
        <div className="mx-auto max-w-7xl">
          <div className="mb-14 text-center">
            <p className="mb-3 text-[10px] font-semibold uppercase tracking-[3px] text-gold">
              How we work
            </p>
            <h2 className="font-serif text-4xl text-white">What guides us</h2>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {values.map((v) => (
              <div
                key={v.title}
                className="rounded-sm border border-purple-light/15 bg-surface/30 p-6"
              >
                <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-full border border-gold/30 bg-gold/10">
                  <v.icon size={18} className="text-gold" />
                </div>
                <h3 className="mb-2.5 font-serif text-lg text-white">{v.title}</h3>
                <p className="text-[13px] leading-relaxed text-muted">{v.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-20 lg:px-10">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="mb-5 font-serif text-4xl text-white">Come see for yourself</h2>
          <p className="mb-9 text-[15px] leading-relaxed text-secondary">
            Book a consultation and we&apos;ll talk through what you want before
            anything is decided.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/booking"
              className="bg-gold px-7 py-3.5 text-[11px] font-semibold uppercase tracking-[2px] text-card transition-all hover:bg-gold-hover"
            >
              Book a Consultation
            </Link>
            <Link
              href="/services"
              className="border border-purple-light/40 px-7 py-3.5 text-[11px] font-semibold uppercase tracking-[2px] text-secondary transition-all hover:border-purple-light hover:text-white"
            >
              View Services
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
