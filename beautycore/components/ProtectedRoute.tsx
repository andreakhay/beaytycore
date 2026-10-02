'use client';

import { useEffect, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth, roleHome } from '@/context/AuthContext';
import type { UserRole } from '@/db/schema';

interface ProtectedRouteProps {
  children: ReactNode;
  /** Role required to view this subtree. Omit to require only that the user is signed in. */
  role?: UserRole;
}

/**
 * Client-side route guard.
 *
 * Note this is a UX guard, not a security boundary — it stops the wrong role
 * seeing the wrong shell. Anything sensitive must also be checked server-side
 * in the route handler (see `requireRole` in lib/auth.ts).
 */
export default function ProtectedRoute({ children, role }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return; // still resolving the session — decide nothing yet

    if (!user) {
      router.replace('/login');
      return;
    }

    // Signed in, but this area belongs to a different role: send them home
    // rather than to the login page, which would look like a failed login.
    if (role && user.role !== role) {
      router.replace(roleHome[user.role]);
    }
  }, [user, loading, role, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0f0520]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-[#b040d8] border-t-transparent" />
          <p className="text-sm tracking-wide text-[#9a7ab8]">Loading…</p>
        </div>
      </div>
    );
  }

  // Redirect is queued in the effect above; render nothing this frame.
  if (!user || (role && user.role !== role)) return null;

  return <>{children}</>;
}
