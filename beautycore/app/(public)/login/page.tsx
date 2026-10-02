import { Suspense } from 'react';
import type { Metadata } from 'next';
import { Loader2 } from 'lucide-react';
import LoginForm from './login-form';

export const metadata: Metadata = {
  title: 'Sign In',
  description: "Sign in to your Andrea's Aesthetic & Wellness Clinic account.",
};

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 size={24} className="animate-spin text-gold" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
