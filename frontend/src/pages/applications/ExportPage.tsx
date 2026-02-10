import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { WizardStepLayout } from '@/components/layout/WizardStepLayout';
import { ResumePreview } from '@/components/application/ResumePreview';
import { CoverLetterPreview } from '@/components/application/CoverLetterPreview';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft, AlertCircle, FileText } from 'lucide-react';
import { getApplication } from '@/api/applications';
import { useGenerateResume } from '@/hooks/useGeneration';

export function ExportPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const appId = Number(id);

  const { data: application, isLoading, isError } = useQuery({
    queryKey: ['application', appId],
    queryFn: () => getApplication(appId),
    enabled: !Number.isNaN(appId),
  });

  const generateResumeMutation = useGenerateResume();

  const handleGenerateResume = () => {
    generateResumeMutation.mutate(appId, {
      onSuccess: () => {
        toast.success('Resume generated', {
          description: 'Your tailored resume is ready for review.',
        });
      },
      onError: (error) => {
        toast.error('Resume generation failed', {
          description: error instanceof Error ? error.message : 'Please try again.',
        });
      },
    });
  };

  // Prerequisites check
  let hasKeywords = false;
  try {
    hasKeywords = !!application?.keywords && JSON.parse(application.keywords).length > 0;
  } catch {
    hasKeywords = false;
  }
  const hasResearch = application?.status === 'reviewed'
    || application?.status === 'generating'
    || application?.status === 'exported'
    || application?.status === 'sent';

  if (isLoading) {
    return (
      <WizardStepLayout currentStep={5}>
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

  if (isError || !application) {
    return (
      <WizardStepLayout currentStep={5}>
        <p className="text-destructive">Failed to load application data</p>
      </WizardStepLayout>
    );
  }

  // Show prerequisites warning if not met
  const prerequisitesMissing = !hasKeywords || !hasResearch;

  return (
    <WizardStepLayout currentStep={5}>
      <Card className="shadow-md">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" aria-hidden="true" />
                Generate Documents: {application.company_name}
              </CardTitle>
              <CardDescription>
                Generate a tailored resume and cover letter for this application
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {prerequisitesMissing && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <div className="ml-2">
                <p className="font-medium">Prerequisites not met</p>
                <ul className="text-sm mt-1 list-disc pl-4">
                  {!hasKeywords && <li>Keywords must be extracted first</li>}
                  {!hasResearch && <li>Research must be approved first</li>}
                </ul>
              </div>
            </Alert>
          )}

          {!prerequisitesMissing && (
            <Tabs defaultValue="resume">
              <TabsList>
                <TabsTrigger value="resume">Resume</TabsTrigger>
                <TabsTrigger value="cover-letter">Cover Letter</TabsTrigger>
              </TabsList>

              <TabsContent value="resume" className="mt-4">
                <ResumePreview
                  resumeContent={application.resume_content}
                  generationStatus={application.generation_status}
                  onGenerate={handleGenerateResume}
                  isGenerating={generateResumeMutation.isPending}
                  error={generateResumeMutation.error}
                  generatedAt={application.resume_content ? application.updated_at : null}
                />
              </TabsContent>

              <TabsContent value="cover-letter" className="mt-4">
                <CoverLetterPreview
                  applicationId={application.id}
                  coverLetterContent={application.cover_letter_content}
                  currentTone={application.cover_letter_tone}
                  generationStatus={application.generation_status}
                />
              </TabsContent>
            </Tabs>
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="mt-8 flex justify-between">
        <Button
          variant="ghost"
          onClick={() => navigate(`/applications/${id}/review`)}
        >
          <ArrowLeft className="h-4 w-4 mr-2" aria-hidden="true" />
          Back
        </Button>
      </div>
    </WizardStepLayout>
  );
}
