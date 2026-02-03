/**
 * User registration page component.
 * Allows users to create a new account with username and password.
 */

import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { register, checkAccountLimit } from '@/api/auth';

export function RegisterPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [registrationAllowed, setRegistrationAllowed] = useState(true);
  const [isCheckingLimit, setIsCheckingLimit] = useState(true);
  const [serviceUnavailable, setServiceUnavailable] = useState(false);

  // Check if registration is allowed on component mount
  useEffect(() => {
    setIsCheckingLimit(true);
    checkAccountLimit()
      .then(({ registration_allowed }) => {
        setRegistrationAllowed(registration_allowed);
        setServiceUnavailable(false);
      })
      .catch((err) => {
        console.error('Failed to check account limit:', err);
        setServiceUnavailable(true);
        setRegistrationAllowed(false);
      })
      .finally(() => {
        setIsCheckingLimit(false);
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Client-side validation
    if (username.length < 3 || username.length > 50) {
      setError('Username must be 3-50 characters');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setIsLoading(true);
    try {
      await register({ username, password });
      navigate('/login');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading state while checking account limit
  if (isCheckingLimit) {
    return (
      <Card className="w-full max-w-md mx-auto mt-20">
        <CardHeader>
          <CardTitle>Loading...</CardTitle>
          <CardDescription>Checking registration availability</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // Show error if service is unavailable
  if (serviceUnavailable) {
    return (
      <Card className="w-full max-w-md mx-auto mt-20">
        <CardHeader>
          <CardTitle>Service Unavailable</CardTitle>
          <CardDescription>
            Unable to connect to the server. Please try again later.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            variant="outline"
            className="w-full"
            onClick={() => window.location.reload()}
          >
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Show message if registration is unavailable (max accounts reached)
  if (!registrationAllowed) {
    return (
      <Card className="w-full max-w-md mx-auto mt-20">
        <CardHeader>
          <CardTitle>Registration Unavailable</CardTitle>
          <CardDescription>Maximum accounts reached (2)</CardDescription>
        </CardHeader>
        <CardContent>
          <Link to="/login">
            <Button variant="outline" className="w-full">
              Go to Login
            </Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md mx-auto mt-20">
      <CardHeader>
        <CardTitle>Create Account</CardTitle>
        <CardDescription>Register to access easy_apply</CardDescription>
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
              placeholder="Enter username (3-50 chars)"
              required
              minLength={3}
              maxLength={50}
              aria-invalid={error ? 'true' : undefined}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password (8+ chars)"
              required
              minLength={8}
              maxLength={128}
              aria-invalid={error ? 'true' : undefined}
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? 'Creating account...' : 'Register'}
          </Button>
          <p className="text-sm text-center text-muted-foreground">
            Already have an account?{' '}
            <Link to="/login" className="text-primary hover:underline">
              Login
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
