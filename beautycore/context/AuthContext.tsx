'use client';

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import { useRouter } from 'next/navigation';
import type { UserRole } from '@/db/schema';

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar: string | null;
}

interface AuthContextValue {
  user: AuthUser | null;
  /** True while the initial session check is in flight. */
  loading: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (name: string, email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  /** Re-reads the session from the server (e.g. after a profile update). */
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Where each role lands after signing in. */
export const roleHome: Record<UserRole, string> = {
  admin: '/admin/dashboard',
  stylist: '/stylist/dashboard',
  client: '/client/dashboard',
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const loadSession = useCallback(async () => {
    try {
      const res = await fetch('/api/auth/session', { cache: 'no-store' });
      const data = await res.json();
      setUser(data.user ?? null);
    } catch {
      setUser(null);
    }
  }, []);

  // Restore the session on first mount so a refresh keeps you signed in.
  useEffect(() => {
    loadSession().finally(() => setLoading(false));
  }, [loadSession]);

  const login = useCallback(
    async (email: string, password: string): Promise<AuthUser> => {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? 'Unable to sign in.');

      setUser(data.user);
      return data.user as AuthUser;
    },
    []
  );

  const register = useCallback(
    async (name: string, email: string, password: string): Promise<AuthUser> => {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? 'Unable to create your account.');

      setUser(data.user);
      return data.user as AuthUser;
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } finally {
      // Clear locally even if the request failed — the user asked to leave.
      setUser(null);
      router.push('/login');
    }
  }, [router]);

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, refresh: loadSession }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside an <AuthProvider>.');
  }
  return ctx;
}
