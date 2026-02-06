import { useNavigate } from 'react-router-dom';
import { JobInputForm } from '@/components/application/JobInputForm';
import { useCreateApplication } from '@/hooks/useApplications';
import { toast } from 'sonner';

export function NewApplicationPage() {
  const navigate = useNavigate();
  const createMutation = useCreateApplication();

  const handleSubmit = async (data: { company_name: string; job_posting: string; job_url?: string }) => {
    try {
      await createMutation.mutateAsync(data);
      toast.success('Application created', {
        description: `${data.company_name} application started`,
      });
      navigate('/dashboard');
    } catch {
      toast.error('Error', {
        description: 'Failed to create application',
      });
    }
  };

  return (
    <div className="container max-w-2xl py-8">
      <h1 className="text-2xl font-bold mb-6">New Application</h1>
      <JobInputForm
        onSubmit={handleSubmit}
        isLoading={createMutation.isPending}
      />
    </div>
  );
}
