import { useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { WizardStepLayout } from '@/components/layout/WizardStepLayout';
import { ResearchSummary } from '@/components/application/ResearchSummary';
import { ApprovalConfirmation } from '@/components/application/ApprovalConfirmation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, FileText, MessageSquare, Pencil, Plus } from 'lucide-react';
import { getApplication, approveResearch } from '@/api/applications';
import { parseResearchData, RESEARCH_CATEGORY_KEYS } from '@/lib/parseResearch';

export function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const appId = Number(id);

  const { data: application, isLoading, isError } = useQuery({
    queryKey: ['application', appId],
    queryFn: () => getApplication(appId),
    enabled: !Number.isNaN(appId),
  });

  const research = application ? parseResearchData(application.research_data) : null;
  const gaps = research?.gaps ?? [];
  const gapToastShown = useRef(false);

  useEffect(() => {
    if (gaps.length > 0 && !gapToastShown.current) {
      gapToastShown.current = true;
      toast.warning('Some research categories had limited results', {
        description:
          'Your application will still be generated using available data. Review the gaps below for details.',
        duration: 8000,
      });
    }
  }, [gaps]);

  const approvalMutation = useMutation({
    mutationFn: () => approveResearch(appId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['application', appId] });
      toast.success('Research approved', {
        description: 'Proceeding to document generation.',
      });
      navigate(`/applications/${id}/export`);
    },
    onError: (error) => {
      toast.error('Approval failed', {
        description: error instanceof Error ? error.message : 'Please try again.',
      });
    },
  });

  const handleApprove = () => {
    approvalMutation.mutate();
  };

  const handleAddContext = () => {
    navigate(`/applications/${id}/context`);
  };

  // If already reviewed or past, redirect to next step
  const isAlreadyApproved = application?.status === 'reviewed'
    || application?.status === 'exported'
    || application?.status === 'sent';

  if (isLoading) {
    return (
      <WizardStepLayout currentStep={4}>
        <Card className="shadow-md">
          <CardHeader>
            <Skeleton className="h-6 w-64" />
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
        <p className="text-destructive">Failed to load application data</p>
      </WizardStepLayout>
    );
  }

  const sourcesFound = research ? RESEARCH_CATEGORY_KEYS.length - gaps.length : 0;

  return (
    <WizardStepLayout currentStep={4}>
      <Card className="shadow-md">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" aria-hidden="true" />
                Research Summary: {application?.company_name}
              </CardTitle>
              <CardDescription>
                Review the research findings before generating your tailored documents
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {research ? (
            <ResearchSummary
              research={research}
              gaps={gaps}
              onAddContext={handleAddContext}
            />
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <p>No research data available.</p>
              <p className="text-sm mt-2">
                Research may still be in progress or there was an error.
              </p>
            </div>
          )}

          {/* Manual Context Display */}
          {application?.manual_context ? (
            <Card className="border-success/20 bg-success/5">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4" aria-hidden="true" />
                    Your Additional Context
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleAddContext}
                  >
                    <Pencil className="h-4 w-4 mr-2" aria-hidden="true" />
                    Edit
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {application.manual_context}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="flex justify-center">
              <Button
                variant="outline"
                onClick={handleAddContext}
              >
                <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
                Add Manual Context
              </Button>
            </div>
          )}

          {/* Approval Section */}
          {research && (
            <ApprovalConfirmation
              sourcesFound={sourcesFound}
              gaps={gaps}
              hasManualContext={!!application?.manual_context}
              onApprove={handleApprove}
              onAddContext={handleAddContext}
              isApproving={approvalMutation.isPending}
            />
          )}

          {/* Navigation - Back only */}
          <div className="flex justify-between pt-4 border-t">
            <Button
              variant="ghost"
              onClick={() => navigate(`/applications/${id}/research`)}
            >
              <ArrowLeft className="h-4 w-4 mr-2" aria-hidden="true" />
              Back
            </Button>
            {isAlreadyApproved && (
              <Button onClick={() => navigate(`/applications/${id}/export`)} size="lg">
                Already Approved - Continue
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </WizardStepLayout>
  );
}
