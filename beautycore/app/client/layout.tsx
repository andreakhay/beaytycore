'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import ClientSidebar from '@/components/ClientSidebar';

export default function ClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute role="client">
      <div className="min-h-screen">
        <ClientSidebar />
        <div className="lg:pl-60">
          <main className="px-6 py-8 lg:px-10">{children}</main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
