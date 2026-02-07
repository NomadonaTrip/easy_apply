import { useNavigate } from 'react-router-dom';
import { JobInputForm } from '@/components/application/JobInputForm';
import { useCreateApplication } from '@/hooks/useApplications';
import { useExtractKeywords } from '@/hooks/useKeywords';
import { useRoleStore } from '@/stores/roleStore';
import { FocusedFlowLayout } from '@/components/layout/FocusedFlowLayout';
import { toast } from 'sonner';

export function NewApplicationPage() {
  const navigate = useNavigate();
  const createMutation = useCreateApplication();
  const extractMutation = useExtractKeywords();
  const roleName = useRoleStore((s) => s.currentRole?.name);

  const isLoading = createMutation.isPending || extractMutation.isPending;

  const handleSubmit = async (data: { company_name: string; job_posting: string; job_url?: string }) => {
    try {
      const application = await createMutation.mutateAsync(data);
      toast.success('Application created', {
        description: `Extracting keywords for ${data.company_name}...`,
      });

      try {
        await extractMutation.mutateAsync(application.id);
      } catch {
        toast.error('Keyword extraction failed', {
          description: 'You can retry from the keywords page.',
        });
      }

      navigate(`/applications/${application.id}/keywords`);
    } catch {
      toast.error('Error', {
        description: 'Failed to create application',
      });
    }
  };

  return (
    <FocusedFlowLayout roleName={roleName} progressStep={1}>
      <h1 className="text-fluid-2xl font-bold mb-6">New Application</h1>
      <JobInputForm
        onSubmit={handleSubmit}
        isLoading={isLoading}
      />
    </FocusedFlowLayout>
  );
}
