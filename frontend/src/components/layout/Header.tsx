import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/authStore';
import { Menu } from 'lucide-react';
import { MobileDrawer } from './MobileDrawer';

export function Header() {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout, isLoggingOut } = useAuthStore();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="border-b bg-background sticky top-0 z-40">
      <div className="container mx-auto px-4 h-12 md:h-14 lg:h-[60px] flex items-center justify-between">
        <Link to="/dashboard" className="flex items-center">
          <h1 className="text-fluid-lg font-semibold">easy_apply</h1>
        </Link>

        {isAuthenticated && user && (
          <>
            {/* Desktop: user info + logout */}
            <div className="hidden lg:flex items-center gap-4">
              <span className="text-sm text-muted-foreground">
                {user.username}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleLogout}
                disabled={isLoggingOut}
              >
                {isLoggingOut ? 'Logging out...' : 'Logout'}
              </Button>
            </div>

            {/* Mobile/Tablet: hamburger */}
            <Button
              variant="ghost"
              size="sm"
              className="lg:hidden"
              onClick={() => setDrawerOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </Button>

            <MobileDrawer open={drawerOpen} onOpenChange={setDrawerOpen} />
          </>
        )}
      </div>
    </header>
  );
}
