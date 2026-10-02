'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import StylistSidebar from '@/components/StylistSidebar';

export default function StylistLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute role="stylist">
      <div className="min-h-screen">
        <StylistSidebar />
        <div className="lg:pl-60">
          <main className="px-6 py-8 lg:px-10">{children}</main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
