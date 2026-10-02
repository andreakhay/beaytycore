'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import AdminSidebar from '@/components/AdminSidebar';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute role="admin">
      <div className="min-h-screen">
        <AdminSidebar />
        <div className="lg:pl-60">
          <main className="px-6 py-8 lg:px-10">{children}</main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
