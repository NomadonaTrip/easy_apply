import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { WizardStepLayout } from '@/components/layout/WizardStepLayout';
import { ManualContextForm } from '@/components/application/ManualContextForm';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import { getManualContext, saveManualContext } from '@/api/applications';

export function ContextPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const appId = Number(id);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['application-context', appId],
    queryFn: () => getManualContext(appId),
    enabled: !Number.isNaN(appId),
  });

  const mutation = useMutation({
    mutationFn: (context: string) => saveManualContext(appId, context),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['application', appId] });
      queryClient.invalidateQueries({
        queryKey: ['application-context', appId],
      });
      toast.success('Context saved', {
        description:
          'Your additional context has been saved and will be used during generation.',
      });
      navigate(`/applications/${id}/review`);
    },
    onError: (error) => {
      toast.error('Failed to save', {
        description:
          error instanceof Error ? error.message : 'Please try again.',
      });
    },
  });

  const handleSave = (context: string) => {
    mutation.mutate(context);
  };

  const handleCancel = () => {
    navigate(`/applications/${id}/review`);
  };

  if (isLoading) {
    return (
      <WizardStepLayout currentStep={4}>
        <Card className="shadow-md">
          <CardHeader>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-96 mt-2" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-48 w-full" />
          </CardContent>
        </Card>
      </WizardStepLayout>
    );
  }

  if (isError) {
    return (
      <WizardStepLayout currentStep={4}>
        <p className="text-destructive">Failed to load context data</p>
      </WizardStepLayout>
    );
  }

  return (
    <WizardStepLayout currentStep={4}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate(`/applications/${id}/review`)}
        className="mb-4"
      >
        <ArrowLeft className="h-4 w-4 mr-2" aria-hidden="true" />
        Back to Review
      </Button>

      <Card className="shadow-md">
        <CardHeader>
          <CardTitle>Add Manual Context</CardTitle>
          <CardDescription>
            Provide additional information about the company that will help
            tailor your application. This is especially useful when automated
            research couldn&apos;t find certain details.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ManualContextForm
            initialValue={data?.manual_context || ''}
            gaps={data?.gaps || []}
            onSave={handleSave}
            onCancel={handleCancel}
            isLoading={mutation.isPending}
          />
        </CardContent>
      </Card>
    </WizardStepLayout>
  );
}
