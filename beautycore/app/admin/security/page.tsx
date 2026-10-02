'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  Shield,
  Search,
  Loader2,
  UserCog,
  Lock,
  KeyRound,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { PageHeader, Card, EmptyState, Skeleton, formatDate } from '@/components/ui';
import { userRoleEnum, type UserRole } from '@/db/schema';

interface UserRow {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  createdAt: string;
  appointmentCount: number;
}

const roleStyle: Record<UserRole, string> = {
  admin: 'border-error/30 bg-error/10 text-error',
  stylist: 'border-info/30 bg-info/10 text-info',
  client: 'border-purple-light/30 bg-purple/15 text-purple-glow',
};

export default function AdminSecurityPage() {
  const { user: currentUser } = useAuth();
  const [rows, setRows] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);

  useEffect(() => {
    fetch('/api/users')
      .then((r) => r.json())
      .then((d) => setRows(d.users ?? []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, []);

  const changeRole = async (id: string, role: UserRole) => {
    setBusy(id);
    setNotice(null);
    try {
      const res = await fetch('/api/users', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, role }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.error ?? 'Could not update role.');

      setRows((rs) => rs.map((r) => (r.id === id ? { ...r, role } : r)));
      setNotice({ kind: 'ok', text: `${d.user.name} is now ${role}.` });
    } catch (err) {
      setNotice({
        kind: 'err',
        text: err instanceof Error ? err.message : 'Could not update role.',
      });
    } finally {
      setBusy(null);
      setTimeout(() => setNotice(null), 4000);
    }
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (r) => r.name.toLowerCase().includes(q) || r.email.toLowerCase().includes(q)
    );
  }, [rows, query]);

  const counts = useMemo(
    () =>
      userRoleEnum.enumValues.map((role) => ({
        role,
        n: rows.filter((r) => r.role === role).length,
      })),
    [rows]
  );

  return (
    <>
      <PageHeader
        title="Security & Access"
        subtitle="Manage who can reach which parts of the system."
      />

      {notice && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mb-6 flex items-center gap-2 rounded-sm border p-4 text-[13px] ${
            notice.kind === 'ok'
              ? 'border-success/30 bg-success/10 text-success'
              : 'border-error/30 bg-error/10 text-error'
          }`}
        >
          {notice.kind === 'ok' ? <CheckCircle size={15} /> : <AlertCircle size={15} />}
          {notice.text}
        </motion.div>
      )}

      {/* Role counts + posture */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {counts.map((c, i) => (
          <motion.div
            key={c.role}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: i * 0.07 }}
          >
            <Card>
              <div className="mb-2.5 flex items-start justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-[1.5px] text-muted">
                  {c.role}s
                </span>
                <UserCog size={15} className="text-muted" />
              </div>
              <p className="font-serif text-3xl text-white">{c.n}</p>
            </Card>
          </motion.div>
        ))}

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.21 }}
        >
          <Card>
            <div className="mb-2.5 flex items-start justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-[1.5px] text-muted">
                Auth
              </span>
              <Shield size={15} className="text-success" />
            </div>
            <p className="mb-1 text-[13px] text-success">Active</p>
            <p className="text-[10px] leading-relaxed text-muted">
              bcrypt hashing · HttpOnly JWT
            </p>
          </Card>
        </motion.div>
      </div>

      {/* Search */}
      <div className="relative mb-6 max-w-md">
        <Search
          size={14}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search users…"
          className="w-full rounded-sm border border-purple-light/20 bg-surface/40 py-2.5 pl-9 pr-4 text-[13px] text-white placeholder-muted focus:border-purple-light focus:outline-none"
        />
      </div>

      {/* User table */}
      <Card>
        <h2 className="mb-5 flex items-center gap-2 font-serif text-xl text-white">
          <KeyRound size={16} className="text-gold" />
          User Accounts
        </h2>

        {loading ? (
          <div className="flex flex-col gap-2">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={UserCog} title="No users match" />
        ) : (
          <div className="scrollbar-thin overflow-x-auto">
            <table className="w-full min-w-[640px]">
              <thead>
                <tr className="border-b border-purple-light/15">
                  {['User', 'Role', 'Bookings', 'Joined', 'Change Role'].map((h) => (
                    <th
                      key={h}
                      className="pb-3 text-left text-[10px] font-semibold uppercase tracking-[1.5px] text-muted"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((u) => {
                  const isSelf = u.id === currentUser?.id;
                  return (
                    <tr key={u.id} className="border-b border-white/[0.04] last:border-0">
                      <td className="py-3.5">
                        <p className="text-[12px] text-white">
                          {u.name}
                          {isSelf && (
                            <span className="ml-2 text-[10px] text-gold">(you)</span>
                          )}
                        </p>
                        <p className="text-[11px] text-muted">{u.email}</p>
                      </td>
                      <td className="py-3.5">
                        <span
                          className={`rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${roleStyle[u.role]}`}
                        >
                          {u.role}
                        </span>
                      </td>
                      <td className="py-3.5 text-[12px] text-secondary">
                        {u.appointmentCount}
                      </td>
                      <td className="py-3.5 text-[11px] text-muted">
                        {formatDate(u.createdAt)}
                      </td>
                      <td className="py-3.5">
                        {isSelf ? (
                          <span className="flex items-center gap-1.5 text-[11px] text-muted">
                            <Lock size={11} />
                            Locked
                          </span>
                        ) : (
                          <span className="flex items-center gap-2">
                            <select
                              value={u.role}
                              onChange={(e) => changeRole(u.id, e.target.value as UserRole)}
                              disabled={busy === u.id}
                              className="rounded-sm border border-purple-light/20 bg-surface/40 px-2.5 py-1.5 text-[11px] text-white focus:border-purple-light focus:outline-none disabled:opacity-50"
                            >
                              {userRoleEnum.enumValues.map((r) => (
                                <option key={r} value={r}>
                                  {r}
                                </option>
                              ))}
                            </select>
                            {busy === u.id && (
                              <Loader2 size={12} className="animate-spin text-gold" />
                            )}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <p className="mt-5 flex items-start gap-2 rounded-sm border border-info/20 bg-info/5 p-3.5 text-[11px] leading-relaxed text-info">
          <Shield size={13} className="mt-0.5 shrink-0" />
          Passwords are hashed with bcrypt and never returned by the API. Sessions
          use signed HttpOnly cookies. You cannot change your own role — this
          prevents locking every admin out of the system.
        </p>
      </Card>
    </>
  );
}
