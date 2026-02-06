import { Link } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useRoleStore } from '@/stores/roleStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export function DashboardPage() {
  const { user } = useAuthStore();
  const currentRole = useRoleStore((s) => s.currentRole);

  return (
    <div className="container mx-auto px-4 py-8">
      <Card>
        <CardHeader>
          <CardTitle>Welcome{user?.username ? `, ${user.username}` : ''}!</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            You have successfully logged in. This is your dashboard.
          </p>
          <p className="text-sm text-muted-foreground mt-4">
            Get started by{' '}
            <Link to="/roles" className="text-primary hover:underline">
              managing your roles
            </Link>
            {' '}to track different career paths.
          </p>
          {currentRole && (
            <div className="mt-6">
              <Button asChild>
                <Link to="/applications/new">New Application</Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
