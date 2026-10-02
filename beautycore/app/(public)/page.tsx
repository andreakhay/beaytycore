'use client';

import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { Sparkles, Scissors, Hand, Flower2, ArrowRight } from 'lucide-react';
import { serviceGroups } from '@/lib/services';

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0 },
};

const highlights = [
  {
    icon: Scissors,
    title: 'Hair Design',
    body: 'Precision cuts, balayage, and colour correction by stylists who read your hair before they touch it.',
    href: '/services#hair-design',
    image: '/hairextension.jpg',
  },
  {
    icon: Hand,
    title: 'Nail Studio',
    body: 'Gel, acrylic, and hand-painted art — finished with products that outlast the week.',
    href: '/services#nail-studio',
    image: '/nails.jpg',
  },
  {
    icon: Flower2,
    title: 'Face & Laser',
    body: 'Medical-grade facials and laser treatments delivered by certified aesthetic specialists.',
    href: '/services#face-laser',
    image: '/makeup.png',
  },
];

export default function HomePage() {
  return (
    <>
      {/* ─── Hero ─────────────────────────────────────────────────────── */}
      <section className="relative flex min-h-[88vh] items-center overflow-hidden px-6 lg:px-10">
        {/* Ambient orbs */}
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <motion.div
            animate={{ x: [0, 40, 0], y: [0, -30, 0], scale: [1, 1.1, 1] }}
            transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute -left-32 top-10 h-[26rem] w-[26rem] rounded-full bg-purple/30 blur-[110px]"
          />
          <motion.div
            animate={{ x: [0, -50, 0], y: [0, 40, 0], scale: [1, 1.15, 1] }}
            transition={{ duration: 22, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
            className="absolute -right-24 bottom-0 h-[30rem] w-[30rem] rounded-full bg-purple-light/20 blur-[120px]"
          />
          <motion.div
            animate={{ opacity: [0.15, 0.3, 0.15] }}
            transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute left-1/2 top-1/3 h-72 w-72 -translate-x-1/2 rounded-full bg-gold/10 blur-[100px]"
          />
        </div>

        <div className="relative mx-auto grid max-w-7xl items-center gap-12 py-20 lg:grid-cols-2">
          <motion.div initial="hidden" animate="show" transition={{ staggerChildren: 0.12 }}>
            <motion.p
              variants={fadeUp}
              transition={{ duration: 0.6 }}
              className="mb-5 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[3px] text-gold"
            >
              <Sparkles size={13} />
              Daet, Camarines Norte
            </motion.p>

            <motion.h1
              variants={fadeUp}
              transition={{ duration: 0.7 }}
              className="mb-6 font-serif text-5xl leading-[1.08] text-white sm:text-6xl lg:text-7xl"
            >
              Beauty, considered
              <span className="block text-gradient-gold">and cared for.</span>
            </motion.h1>

            <motion.p
              variants={fadeUp}
              transition={{ duration: 0.7 }}
              className="mb-4 max-w-lg text-[15px] leading-relaxed text-secondary"
            >
              Hair, nails, skin, and wellness under one roof — with an AI advisor
              that reads your photo and recommends what genuinely suits you.
            </motion.p>

            <motion.p
              variants={fadeUp}
              transition={{ duration: 0.7 }}
              className="mb-9 font-serif text-lg italic text-muted"
            >
              &ldquo;Self-care is not an indulgence. It&apos;s a necessity.&rdquo;
            </motion.p>

            <motion.div variants={fadeUp} transition={{ duration: 0.7 }} className="flex flex-wrap gap-3">
              <Link
                href="/booking"
                className="group flex items-center gap-2 bg-gold px-7 py-3.5 text-[11px] font-semibold uppercase tracking-[2px] text-card transition-all hover:bg-gold-hover"
              >
                Book an Appointment
                <ArrowRight size={14} className="transition-transform group-hover:translate-x-1" />
              </Link>
              <Link
                href="/client/ai-advisor"
                className="flex items-center gap-2 border border-purple-light/40 px-7 py-3.5 text-[11px] font-semibold uppercase tracking-[2px] text-secondary transition-all hover:border-purple-light hover:text-white"
              >
                <Sparkles size={14} />
                Try the AI Advisor
              </Link>
            </motion.div>
          </motion.div>

          {/* Hero image */}
          <motion.div
            initial={{ opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.9, ease: 'easeOut' }}
            className="relative hidden lg:block"
          >
            <div className="relative aspect-[4/5] overflow-hidden rounded-sm border border-purple-light/20">
              <Image
                src="/aboutpic.jpg"
                alt="Andrea's Aesthetic & Wellness Clinic"
                fill
                priority
                sizes="(max-width: 1024px) 100vw, 50vw"
                className="object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-deep via-transparent to-transparent" />
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─── Services ─────────────────────────────────────────────────── */}
      <section className="px-6 py-24 lg:px-10">
        <div className="mx-auto max-w-7xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.6 }}
            className="mb-14 text-center"
          >
            <p className="mb-3 text-[10px] font-semibold uppercase tracking-[3px] text-gold">
              What we do
            </p>
            <h2 className="font-serif text-4xl text-white sm:text-5xl">
              Every detail, deliberate
            </h2>
          </motion.div>

          <div className="grid gap-6 md:grid-cols-3">
            {highlights.map((h, i) => (
              <motion.div
                key={h.title}
                initial={{ opacity: 0, y: 28 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-60px' }}
                transition={{ duration: 0.55, delay: i * 0.12 }}
              >
                <Link
                  href={h.href}
                  className="group relative block h-full overflow-hidden rounded-sm border border-purple-light/15 bg-card transition-colors hover:border-gold/50"
                >
                  <div className="relative h-44 overflow-hidden">
                    <Image
                      src={h.image}
                      alt={h.title}
                      fill
                      sizes="(max-width: 768px) 100vw, 33vw"
                      className="object-cover transition-transform duration-700 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-card via-card/40 to-transparent" />
                  </div>

                  <div className="p-6">
                    <h3 className="mb-2.5 flex items-center gap-2 font-serif text-xl text-white">
                      <h.icon size={17} className="text-gold" />
                      {h.title}
                    </h3>
                    <p className="mb-4 text-[13px] leading-relaxed text-muted">{h.body}</p>
                    <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[1.5px] text-gold">
                      Explore
                      <ArrowRight size={12} className="transition-transform group-hover:translate-x-1" />
                    </span>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>

          {/* Everything else */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mt-10 flex flex-wrap justify-center gap-2.5"
          >
            {serviceGroups.map((g) => (
              <Link
                key={g.id}
                href={`/services#${g.id}`}
                className="rounded-full border border-purple-light/20 px-4 py-2 text-[11px] text-muted transition-colors hover:border-gold/40 hover:text-gold"
              >
                {g.label}
              </Link>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ─── AI Advisor ───────────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-y border-purple-light/15 bg-card px-6 py-24 lg:px-10">
        <div
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-1/2 h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full bg-purple/20 blur-[120px]"
        />
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.7 }}
          className="relative mx-auto max-w-2xl text-center"
        >
          <div className="mb-6 inline-flex h-14 w-14 items-center justify-center rounded-full border border-gold/30 bg-gold/10">
            <Sparkles size={22} className="text-gold" />
          </div>
          <h2 className="mb-5 font-serif text-4xl text-white sm:text-5xl">
            Not sure what suits you?
          </h2>
          <p className="mb-8 text-[15px] leading-relaxed text-secondary">
            Upload a photo of your hair or nails. Our AI advisor reads what&apos;s
            actually there — length, tone, shape, condition — and suggests three
            styles with the reasoning behind each one.
          </p>
          <Link
            href="/client/ai-advisor"
            className="group inline-flex items-center gap-2 bg-gold px-8 py-3.5 text-[11px] font-semibold uppercase tracking-[2px] text-card transition-all hover:bg-gold-hover"
          >
            Get a Recommendation
            <ArrowRight size={14} className="transition-transform group-hover:translate-x-1" />
          </Link>
        </motion.div>
      </section>

      {/* ─── Closing CTA ──────────────────────────────────────────────── */}
      <section className="px-6 py-24 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="mx-auto max-w-3xl text-center"
        >
          <h2 className="mb-5 font-serif text-4xl text-white sm:text-5xl">
            We&apos;d love to see you
          </h2>
          <p className="mb-9 text-[15px] leading-relaxed text-secondary">
            Open Monday to Saturday, 9AM–8PM. Sundays 10AM–6PM.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/booking"
              className="bg-gold px-7 py-3.5 text-[11px] font-semibold uppercase tracking-[2px] text-card transition-all hover:bg-gold-hover"
            >
              Book Now
            </Link>
            <Link
              href="/contact"
              className="border border-purple-light/40 px-7 py-3.5 text-[11px] font-semibold uppercase tracking-[2px] text-secondary transition-all hover:border-purple-light hover:text-white"
            >
              Contact Us
            </Link>
          </div>
        </motion.div>
      </section>
    </>
  );
}
