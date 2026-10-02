'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X, LogOut, type LucideIcon } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export interface SidebarLink {
  href: string;
  label: string;
  icon: LucideIcon;
}

interface SidebarProps {
  links: SidebarLink[];
  /** Shown under the wordmark, e.g. "Admin Portal". */
  portalLabel: string;
}

/**
 * Shared sidebar shell for the admin, stylist, and client portals.
 * Fixed rail on desktop; slide-over drawer under `lg`.
 */
export default function Sidebar({ links, portalLabel }: SidebarProps) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // Close the drawer whenever the route changes.
  useEffect(() => setOpen(false), [pathname]);

  // Lock body scroll while the mobile drawer is open.
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  const initials = user?.name
    ? user.name
        .split(' ')
        .map((n) => n[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : '··';

  const nav = (
    <div className="flex h-full flex-col">
      {/* Wordmark */}
      <div className="border-b border-purple-light/15 px-6 py-6">
        <Link href="/" className="flex flex-col leading-tight">
          <span className="font-serif text-base font-semibold tracking-[3px] text-white">
            ANDREA&apos;S
          </span>
          <span className="text-[8px] uppercase tracking-[2px] text-gold">
            {portalLabel}
          </span>
        </Link>
      </div>

      {/* Links */}
      <nav className="scrollbar-thin flex-1 overflow-y-auto px-3 py-5">
        <ul className="flex flex-col gap-1">
          {links.map(({ href, label, icon: Icon }) => {
            // Exact match, or a nested route below this link.
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={active ? 'page' : undefined}
                  className={`relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-[12px] font-medium transition-colors ${
                    active
                      ? 'bg-purple/25 text-white'
                      : 'text-muted hover:bg-surface/40 hover:text-secondary'
                  }`}
                >
                  {active && (
                    <motion.span
                      layoutId="sidebar-active"
                      className="absolute left-0 h-6 w-[3px] rounded-r bg-gold"
                    />
                  )}
                  <Icon size={16} className={active ? 'text-gold' : ''} />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* User footer */}
      <div className="border-t border-purple-light/15 p-4">
        <div className="mb-3 flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-purple text-[11px] font-semibold text-white">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[12px] font-medium text-white">
              {user?.name ?? 'Loading…'}
            </p>
            <p className="truncate text-[10px] capitalize text-muted">
              {user?.role}
            </p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-[11px] font-medium text-muted transition-colors hover:bg-error/10 hover:text-error"
        >
          <LogOut size={14} />
          Sign Out
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile top bar */}
      <div className="sticky top-0 z-40 flex items-center justify-between border-b border-purple-light/15 bg-card px-4 py-3 lg:hidden">
        <span className="font-serif text-sm font-semibold tracking-[2px] text-white">
          ANDREA&apos;S
        </span>
        <button
          onClick={() => setOpen(true)}
          aria-label="Open navigation"
          className="p-1 text-white"
        >
          <Menu size={20} />
        </button>
      </div>

      {/* Desktop rail */}
      <aside className="fixed left-0 top-0 hidden h-screen w-60 border-r border-purple-light/15 bg-card lg:block">
        {nav}
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-50 bg-black/60 lg:hidden"
            />
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'tween', duration: 0.25, ease: 'easeOut' }}
              className="fixed left-0 top-0 z-50 h-screen w-64 border-r border-purple-light/15 bg-card lg:hidden"
            >
              <button
                onClick={() => setOpen(false)}
                aria-label="Close navigation"
                className="absolute right-3 top-5 p-1 text-muted hover:text-white"
              >
                <X size={18} />
              </button>
              {nav}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
