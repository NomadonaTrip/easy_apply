import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { WizardStepLayout } from '@/components/layout/WizardStepLayout';
import { ResearchSummary } from '@/components/application/ResearchSummary';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowRight, ArrowLeft, FileText } from 'lucide-react';
import { getApplication } from '@/api/applications';
import { parseResearchData } from '@/lib/parseResearch';

export function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const appId = Number(id);

  const { data: application, isLoading, isError } = useQuery({
    queryKey: ['application', appId],
    queryFn: () => getApplication(appId),
    enabled: !Number.isNaN(appId),
  });

  const research = application ? parseResearchData(application.research_data) : null;
  const gaps = research?.gaps ?? [];

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
            <ResearchSummary research={research} gaps={gaps} />
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <p>No research data available.</p>
              <p className="text-sm mt-2">
                Research may still be in progress or there was an error.
              </p>
            </div>
          )}

          {/* Navigation */}
          <div className="flex justify-between pt-4 border-t">
            <Button
              variant="ghost"
              onClick={() => navigate(`/applications/${id}/research`)}
            >
              <ArrowLeft className="h-4 w-4 mr-2" aria-hidden="true" />
              Back
            </Button>
            <Button onClick={() => navigate(`/applications/${id}/export`)} size="lg">
              Continue to Generation
              <ArrowRight className="h-4 w-4 ml-2" aria-hidden="true" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </WizardStepLayout>
  );
}
