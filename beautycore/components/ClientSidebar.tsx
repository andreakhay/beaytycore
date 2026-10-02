'use client';

import {
  LayoutDashboard,
  Sparkles,
  Hand,
  Scissors,
  WandSparkles,
  CalendarDays,
  UserCircle,
} from 'lucide-react';
import Sidebar, { type SidebarLink } from './Sidebar';

const links: SidebarLink[] = [
  { href: '/client/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/client/ai-consultation', label: 'AI Consultation', icon: Sparkles },
  { href: '/client/nail-studio', label: 'Nail Studio', icon: Hand },
  { href: '/client/hair-studio', label: 'Hair Studio', icon: Scissors },
  { href: '/client/makeup-studio', label: 'Makeup Studio', icon: WandSparkles },
  { href: '/client/appointments', label: 'Appointments', icon: CalendarDays },
  { href: '/client/profile', label: 'Profile', icon: UserCircle },
];

export default function ClientSidebar() {
  return <Sidebar links={links} portalLabel="Client Portal" />;
}
