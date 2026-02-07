import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RoleCreateForm } from '@/components/roles/RoleCreateForm';
import { useRoles, useDeleteRole } from '@/hooks/useRoles';
import { Trash2 } from 'lucide-react';

export function RolesPage() {
  const { data: roles, isLoading, error } = useRoles();
  const deleteRole = useDeleteRole();

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <p className="text-muted-foreground">Loading roles...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <p className="text-destructive">Failed to load roles</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <h1 className="text-fluid-2xl font-bold">Manage Roles</h1>

      <Card>
        <CardHeader>
          <CardTitle>Add New Role</CardTitle>
        </CardHeader>
        <CardContent>
          <RoleCreateForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Your Roles</CardTitle>
        </CardHeader>
        <CardContent>
          {deleteRole.isError && (
            <p className="text-sm text-destructive mb-4">
              Failed to delete role. Please try again.
            </p>
          )}
          {roles && roles.length > 0 ? (
            <ul className="space-y-2">
              {roles.map((role) => (
                <li
                  key={role.id}
                  className="flex items-center justify-between p-3 bg-muted rounded-md"
                >
                  <span className="font-medium">{role.name}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteRole.mutate(role.id)}
                    disabled={deleteRole.isPending}
                    aria-label={`Delete ${role.name}`}
                  >
                    {deleteRole.isPending ? (
                      <span className="text-xs text-muted-foreground">...</span>
                    ) : (
                      <Trash2 className="h-4 w-4 text-destructive" />
                    )}
                  </Button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="flex flex-col items-center justify-center text-center py-12">
              <p className="text-muted-foreground mb-4">
                Create your first role to get started
              </p>
              <Button onClick={() => document.getElementById('role-name')?.focus()}>
                Create Role
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
