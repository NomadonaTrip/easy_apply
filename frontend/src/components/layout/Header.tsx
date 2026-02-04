import { useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
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
      <div className="container mx-auto px-4 h-14 flex items-center justify-between">
        <h1 className="text-lg font-semibold">easy_apply</h1>

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
