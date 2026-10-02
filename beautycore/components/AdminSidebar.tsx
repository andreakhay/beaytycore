'use client';

import {
  LayoutDashboard,
  CalendarDays,
  Users,
  Package,
  Wallet,
  TrendingUp,
  ShieldCheck,
} from 'lucide-react';
import Sidebar, { type SidebarLink } from './Sidebar';

const links: SidebarLink[] = [
  { href: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/admin/appointments', label: 'Appointments', icon: CalendarDays },
  { href: '/admin/clients', label: 'Clients', icon: Users },
  { href: '/admin/inventory', label: 'Inventory', icon: Package },
  { href: '/admin/finance', label: 'Finance', icon: Wallet },
  { href: '/admin/market-trends', label: 'Market Trends', icon: TrendingUp },
  { href: '/admin/security', label: 'Security', icon: ShieldCheck },
];

export default function AdminSidebar() {
  return <Sidebar links={links} portalLabel="Admin Portal" />;
}
