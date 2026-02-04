import { useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { RoleSelector } from '@/components/roles/RoleSelector';
import { useAuthStore } from '@/stores/authStore';

export function Header() {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout, isLoggingOut } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="border-b bg-background">
      <div className="container mx-auto px-4 h-[60px] flex items-center justify-between">
        <div className="flex items-center gap-6">
          <h1 className="text-lg font-semibold">easy_apply</h1>
          {isAuthenticated && user && <RoleSelector />}
        </div>

        {isAuthenticated && user && (
          <div className="flex items-center gap-4">
            <Link
              to="/roles"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Manage Roles
            </Link>
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
        )}
      </div>
    </header>
  );
}
