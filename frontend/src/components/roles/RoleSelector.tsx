import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useRoles } from '@/hooks/useRoles';
import { useRoleStore } from '@/stores/roleStore';

export function RoleSelector() {
  const { data: roles, isLoading } = useRoles();
  const { currentRole, setCurrentRole } = useRoleStore();

  const handleRoleChange = (roleId: string) => {
    const selectedRole = roles?.find((r) => r.id === parseInt(roleId, 10));
    if (selectedRole) {
      setCurrentRole(selectedRole);
    }
  };

  if (isLoading) {
    return (
      <div className="h-10 w-40 bg-muted animate-pulse rounded-md" />
    );
  }

  if (!roles || roles.length === 0) {
    return (
      <span className="text-sm text-muted-foreground">
        No roles - create one first
      </span>
    );
  }

  return (
    <Select
      value={currentRole?.id?.toString() || ''}
      onValueChange={handleRoleChange}
    >
      <SelectTrigger className="w-[200px]">
        <SelectValue placeholder="Select a role" />
      </SelectTrigger>
      <SelectContent>
        {roles.map((role) => (
          <SelectItem key={role.id} value={role.id.toString()}>
            {role.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
