import { NavLink, useNavigate } from 'react-router-dom';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { RoleSelector } from '@/components/roles/RoleSelector';
import { useAuthStore } from '@/stores/authStore';
import { mainNavItems } from '@/config/navItems';

interface MobileDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function MobileDrawer({ open, onOpenChange }: MobileDrawerProps) {
  const navigate = useNavigate();
  const { user, logout, isLoggingOut } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    onOpenChange(false);
    navigate('/login');
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[280px] p-0">
        <SheetHeader className="border-b px-4 py-4">
          <SheetTitle className="text-left text-sm font-medium">Menu</SheetTitle>
          <SheetDescription className="sr-only">Application navigation and settings</SheetDescription>
        </SheetHeader>

        <div className="px-4 py-4 border-b">
          <RoleSelector />
        </div>

        <nav className="flex-1 py-2 overflow-y-auto" aria-label="Mobile navigation">
          {mainNavItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => onOpenChange(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 text-sm transition-colors ${
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

        {user && (
          <div className="border-t px-4 py-4">
            <p className="text-sm text-muted-foreground mb-3">{user.username}</p>
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={handleLogout}
              disabled={isLoggingOut}
            >
              {isLoggingOut ? 'Logging out...' : 'Logout'}
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
