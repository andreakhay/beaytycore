'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X, LayoutDashboard, LogOut } from 'lucide-react';
import { useAuth, roleHome } from '@/context/AuthContext';

const links = [
  { href: '/', label: 'Home' },
  { href: '/services', label: 'Services' },
  { href: '/about', label: 'About' },
  { href: '/contact', label: 'Contact' },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();

  // Solidify the bar once the hero scrolls under it.
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Close the mobile menu on navigation.
  useEffect(() => setOpen(false), [pathname]);

  return (
    <nav
      className={`sticky top-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'glass border-b border-purple-light/20 shadow-lg shadow-black/20'
          : 'border-b border-transparent bg-card/40'
      }`}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-10">
        {/* Wordmark */}
        <Link href="/" className="flex flex-col leading-tight">
          <span className="font-serif text-lg font-semibold tracking-[3px] text-white">
            ANDREA&apos;S
          </span>
          <span className="text-[8px] uppercase tracking-[2px] text-gold">
            Aesthetic &amp; Wellness Clinic
          </span>
        </Link>

        {/* Desktop links */}
        <ul className="hidden items-center gap-8 lg:flex">
          {links.map((l) => {
            const active = pathname === l.href;
            return (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className={`relative text-[11px] font-medium uppercase tracking-[1.5px] transition-colors ${
                    active ? 'text-gold' : 'text-secondary hover:text-gold'
                  }`}
                >
                  {l.label}
                  {active && (
                    <motion.span
                      layoutId="nav-underline"
                      className="absolute -bottom-1.5 left-0 h-px w-full bg-gold"
                    />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Desktop auth actions */}
        <div className="hidden items-center gap-3 lg:flex">
          {loading ? (
            <div className="h-8 w-28 animate-pulse rounded bg-surface/60" />
          ) : user ? (
            <>
              <Link
                href={roleHome[user.role]}
                className="flex items-center gap-2 rounded border border-purple-light/40 px-4 py-2 text-[10px] font-semibold uppercase tracking-[1.5px] text-secondary transition-colors hover:border-purple-light hover:text-white"
              >
                <LayoutDashboard size={13} />
                Dashboard
              </Link>
              <button
                onClick={logout}
                aria-label="Sign out"
                className="rounded p-2 text-muted transition-colors hover:text-error"
              >
                <LogOut size={16} />
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="text-[10px] font-semibold uppercase tracking-[2px] text-secondary transition-colors hover:text-gold"
              >
                Sign In
              </Link>
              <Link
                href="/booking"
                className="border border-gold px-[18px] py-2 text-[10px] font-semibold uppercase tracking-[2px] text-gold transition-all hover:bg-gold hover:text-card"
              >
                Book Now
              </Link>
            </>
          )}
        </div>

        {/* Mobile toggle */}
        <button
          onClick={() => setOpen((o) => !o)}
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
          className="p-1 text-white lg:hidden"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile drawer */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="overflow-hidden border-t border-purple-light/15 bg-card lg:hidden"
          >
            <ul className="px-6 py-2">
              {links.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    className={`block border-b border-white/5 py-3 text-[11px] uppercase tracking-[1.5px] ${
                      pathname === l.href ? 'text-gold' : 'text-secondary'
                    }`}
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>

            <div className="flex flex-col gap-2 px-6 pb-5 pt-2">
              {user ? (
                <>
                  <Link
                    href={roleHome[user.role]}
                    className="border border-purple-light/40 px-4 py-2.5 text-center text-[10px] font-semibold uppercase tracking-[1.5px] text-secondary"
                  >
                    Dashboard
                  </Link>
                  <button
                    onClick={logout}
                    className="px-4 py-2.5 text-center text-[10px] font-semibold uppercase tracking-[1.5px] text-error"
                  >
                    Sign Out
                  </button>
                </>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="border border-purple-light/40 px-4 py-2.5 text-center text-[10px] font-semibold uppercase tracking-[1.5px] text-secondary"
                  >
                    Sign In
                  </Link>
                  <Link
                    href="/booking"
                    className="border border-gold bg-gold px-4 py-2.5 text-center text-[10px] font-semibold uppercase tracking-[2px] text-card"
                  >
                    Book Now
                  </Link>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
