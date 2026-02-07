import { NavLink } from 'react-router-dom';
import { bottomNavItems } from '@/config/navItems';

export function MobileBottomNav() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 h-14 border-t bg-background lg:hidden pb-[env(safe-area-inset-bottom)]"
      aria-label="Main navigation"
    >
      <div className="flex h-full items-center justify-around">
        {bottomNavItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 px-3 py-1 text-xs transition-colors ${
                isActive
                  ? 'text-primary font-semibold border-t-2 border-primary'
                  : 'text-muted-foreground border-t-2 border-transparent'
              }`
            }
          >
            <Icon className="h-5 w-5" />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
