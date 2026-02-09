import { useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { WizardStepLayout } from '@/components/layout/WizardStepLayout';
import { useResearchStream, RESEARCH_CATEGORIES } from '@/hooks/useResearchStream';
import { ResearchProgress } from '@/components/application/ResearchProgress';
import { getApplication } from '@/api/applications';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, ArrowRight, RotateCcw } from 'lucide-react';

export function ResearchPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const applicationId = Number(id);
  const hasStartedRef = useRef(false);

  const { data: application, isLoading } = useQuery({
    queryKey: ['application', applicationId],
    queryFn: () => getApplication(applicationId),
  });

  const {
    sources,
    isComplete,
    isError,
    error,
    progress,
    startResearch,
    retryConnection,
  } = useResearchStream(applicationId);

  // Auto-start research when application loads and is in 'keywords' status
  useEffect(() => {
    if (application && application.status === 'keywords' && !isComplete && !isError && !hasStartedRef.current) {
      hasStartedRef.current = true;
      startResearch();
    }
  }, [application, startResearch, isComplete, isError]);

  const handleContinue = () => {
    navigate(`/applications/${id}/review`);
  };

  if (isLoading) {
    return (
      <WizardStepLayout currentStep={3}>
        <Card className="shadow-md">
          <CardContent className="p-6">
            <div className="animate-pulse space-y-4">
              <div className="h-6 bg-muted rounded w-48" />
              <div className="h-2 bg-muted rounded" />
              <div className="space-y-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="h-16 bg-muted rounded-lg" />
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </WizardStepLayout>
    );
  }

  // Research already completed — show completed state
  if (application?.research_data && !isComplete && !hasStartedRef.current) {
    return (
      <WizardStepLayout currentStep={3}>
        <Card className="shadow-md">
          <CardHeader>
            <CardTitle>Researching {application.company_name}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <ResearchProgress
              sources={RESEARCH_CATEGORIES.map((s) => ({
                source: s.source,
                status: 'complete' as const,
                found: true,
              }))}
              progress={100}
              isComplete={true}
            />
            <div className="pt-4 border-t">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-success">Research Complete</p>
                  <p className="text-sm text-muted-foreground">
                    Review the findings before generating your documents.
                  </p>
                </div>
                <Button onClick={handleContinue}>
                  Continue to Review
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
        <div className="mt-8 flex justify-start">
          <Button variant="ghost" onClick={() => navigate(`/applications/${id}/keywords`)}>
            Back
          </Button>
        </div>
      </WizardStepLayout>
    );
  }

  return (
    <WizardStepLayout currentStep={3}>
      <Card className="shadow-md">
        <CardHeader>
          <CardTitle>Researching {application?.company_name}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>{error}</span>
                <Button variant="outline" size="sm" onClick={retryConnection}>
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          )}

          <ResearchProgress sources={sources} progress={progress} isComplete={isComplete} />

          {isComplete && (
            <div className="pt-4 border-t">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-success">Research Complete</p>
                  <p className="text-sm text-muted-foreground">
                    Review the findings before generating your documents.
                  </p>
                </div>
                <Button onClick={handleContinue}>
                  Continue to Review
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </div>
          )}

          {!isComplete && !isError && application?.status !== 'keywords' && (
            <div className="flex justify-center">
              <Button onClick={startResearch}>Start Research</Button>
            </div>
          )}
        </CardContent>
      </Card>
      <div className="mt-8 flex justify-start">
        <Button variant="ghost" onClick={() => navigate(`/applications/${id}/keywords`)}>
          Back
        </Button>
      </div>
    </WizardStepLayout>
  );
}
