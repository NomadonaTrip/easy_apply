import { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useAuthStore } from '@/stores/authStore';
import { login, checkAccountLimit } from '@/api/auth';

interface LocationState {
  from?: { pathname: string };
}

function isLocationState(state: unknown): state is LocationState {
  if (typeof state !== 'object' || state === null) {
    return false;
  }
  if (!('from' in state)) {
    return true; // Empty object is valid
  }
  const s = state as { from?: unknown };
  if (typeof s.from !== 'object' || s.from === null) {
    return false;
  }
  return typeof (s.from as { pathname?: unknown }).pathname === 'string';
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, setUser } = useAuthStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Check if registration is allowed
  const { data: accountLimit, isLoading: isAccountLimitLoading } = useQuery({
    queryKey: ['accountLimit'],
    queryFn: checkAccountLimit,
    staleTime: 60 * 1000, // Cache for 1 minute
  });

  // Get the page user tried to access before being redirected (with type safety)
  const from = isLocationState(location.state)
    ? location.state.from?.pathname ?? '/dashboard'
    : '/dashboard';

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const user = await login({ username, password });
      setUser(user);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[80vh]">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Login</CardTitle>
          <CardDescription>Sign in to access easy_apply</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                required
                autoComplete="username"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
                autoComplete="current-password"
              />
            </div>
            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? 'Signing in...' : 'Login'}
            </Button>
            {!isAccountLimitLoading && accountLimit?.registration_allowed && (
              <p className="text-sm text-center text-muted-foreground">
                Don't have an account?{' '}
                <Link to="/register" className="text-primary hover:underline">
                  Register
                </Link>
              </p>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
