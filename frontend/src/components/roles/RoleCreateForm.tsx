import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useCreateRole } from '@/hooks/useRoles';

const MAX_ROLE_NAME_LENGTH = 100;

export function RoleCreateForm() {
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const createRole = useCreateRole();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedName = name.trim();
    if (!trimmedName) {
      setError('Role name is required');
      return;
    }

    if (trimmedName.length > MAX_ROLE_NAME_LENGTH) {
      setError(`Role name must be ${MAX_ROLE_NAME_LENGTH} characters or less`);
      return;
    }

    createRole.mutate(
      { name: trimmedName },
      {
        onSuccess: () => {
          setName('');
          setError(null);
        },
        onError: () => {
          setError('Failed to create role');
        },
      }
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="role-name">Role Name</Label>
        <Input
          id="role-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Product Manager"
          disabled={createRole.isPending}
        />
        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}
      </div>
      <Button type="submit" disabled={createRole.isPending}>
        {createRole.isPending ? 'Creating...' : 'Add Role'}
      </Button>
    </form>
  );
}
