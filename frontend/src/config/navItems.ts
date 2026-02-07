import { LayoutDashboard, Plus, Database, Settings, User } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface NavItem {
  to: string;
  icon: LucideIcon;
  label: string;
}

/** Full navigation — used in Sidebar and MobileDrawer */
export const mainNavItems: NavItem[] = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/applications/new', icon: Plus, label: 'New Application' },
  { to: '/experience', icon: Database, label: 'Experience DB' },
  { to: '/roles', icon: Settings, label: 'Manage Roles' },
];

/** Condensed bottom-bar items — used in MobileBottomNav */
export const bottomNavItems: NavItem[] = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/applications/new', icon: Plus, label: 'New App' },
  { to: '/roles', icon: User, label: 'Profile' },
];
