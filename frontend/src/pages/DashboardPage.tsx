import { Link } from 'react-router-dom';
import { useApplications } from '@/hooks/useApplications';
import { useRoleStore } from '@/stores/roleStore';
import { ApplicationCard } from '@/components/dashboard/ApplicationCard';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

export function DashboardPage() {
  const currentRole = useRoleStore((s) => s.currentRole);
  const { data: applications, isLoading } = useApplications();

  if (!currentRole) {
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <p className="text-muted-foreground mb-4">
          Select a role to get started.
        </p>
        <Link to="/roles">
          <Button>Manage Roles</Button>
        </Link>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  // Sort by updated_at descending
  const sortedApps = [...(applications || [])].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  );

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Applications</h1>
        <Link to="/applications/new">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            New Application
          </Button>
        </Link>
      </div>

      {sortedApps.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">
            No applications yet. Create your first application to get started.
          </p>
          <Link to="/applications/new">
            <Button>Create Application</Button>
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {sortedApps.map((app) => (
            <ApplicationCard key={app.id} application={app} />
          ))}
        </div>
      )}
    </div>
  );
}
