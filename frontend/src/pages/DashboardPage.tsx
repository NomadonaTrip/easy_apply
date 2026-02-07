import { Link } from 'react-router-dom';
import { useApplications } from '@/hooks/useApplications';
import { useRoleStore } from '@/stores/roleStore';
import { CommandCenterLayout } from '@/components/layout/CommandCenterLayout';
import { StatsGrid } from '@/components/dashboard/StatsGrid';
import { ApplicationTable } from '@/components/dashboard/ApplicationTable';
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
      <CommandCenterLayout>
        <div className="p-4 lg:p-8">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      </CommandCenterLayout>
    );
  }

  const sortedApps = [...(applications || [])].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  );

  return (
    <CommandCenterLayout>
      <div className="p-4 lg:p-8">
        <div className="flex items-center justify-between mb-6 lg:mb-8">
          <h1 className="text-fluid-3xl font-bold">Applications</h1>
          <Link to="/applications/new">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              New Application
            </Button>
          </Link>
        </div>

        {sortedApps.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center py-12">
            <p className="text-muted-foreground mb-4">
              No applications yet
            </p>
            <Link to="/applications/new">
              <Button>New Application</Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            <StatsGrid applications={sortedApps} />
            <ApplicationTable applications={sortedApps} />
          </div>
        )}
      </div>
    </CommandCenterLayout>
  );
}
