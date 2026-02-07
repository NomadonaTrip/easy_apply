import { NavLink } from 'react-router-dom';
import { RoleSelector } from '@/components/roles/RoleSelector';
import { mainNavItems } from '@/config/navItems';

export function Sidebar() {
  return (
    <aside className="hidden lg:flex flex-col w-[240px] xl:w-[280px] border-r bg-sidebar min-h-0">
      <div className="px-4 py-4 border-b">
        <RoleSelector />
      </div>
      <nav className="flex-1 py-2" aria-label="Main navigation">
        {mainNavItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 mx-2 px-3 py-2 text-sm rounded-md transition-colors ${
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
