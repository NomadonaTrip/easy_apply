import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useAutoSelectRole } from '@/hooks/useAutoSelectRole';

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuthStore();
  const location = useLocation();

  // Auto-select role when authenticated (runs for all protected routes)
  const { needsRoleCreation } = useAutoSelectRole();

  // Show loading state while checking auth
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-muted-foreground">Checking authentication...</div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    // Save the attempted URL for redirecting after login
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Redirect to roles page if user needs to create a role
  if (needsRoleCreation && location.pathname !== '/roles') {
    return <Navigate to="/roles" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
