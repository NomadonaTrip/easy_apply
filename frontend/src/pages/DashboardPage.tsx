import { useAuthStore } from '@/stores/authStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function DashboardPage() {
  const { user } = useAuthStore();

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
            Role management and application features will be added in future epics.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
