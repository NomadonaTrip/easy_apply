import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ApplicationStatusBadge } from '@/components/application/ApplicationStatusBadge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { WizardStepLayout } from '@/components/layout/WizardStepLayout';
import { formatDistanceToNow } from 'date-fns';
import { getApplication } from '@/api/applications';
import { ArrowLeft, ListChecks } from 'lucide-react';

const STATUS_TO_STEP: Record<string, number> = {
  created: 1,
  keywords: 2,
  researching: 3,
  reviewed: 4,
  exported: 5,
  sent: 5,
  callback: 5,
  offer: 5,
  closed: 5,
};

export function ApplicationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: application, isLoading } = useQuery({
    queryKey: ['application', id],
    queryFn: () => getApplication(Number(id)),
  });

  const handleContinue = () => {
    const nextStep: Record<string, string> = {
      created: 'keywords',
      keywords: 'research',
      researching: 'research',
      reviewed: 'review',
      exported: 'export',
    };
    const status = application?.status || 'created';
    const next = nextStep[status];
    if (next) {
      navigate(`/applications/${id}/${next}`);
    }
  };

  if (isLoading) {
    return (
      <WizardStepLayout currentStep={1}>
        <Skeleton className="h-5 w-32 mb-4" />
        <Skeleton className="h-10 w-64 mb-2" />
        <Skeleton className="h-5 w-48 mb-8" />
        <Skeleton className="h-48 w-full" />
      </WizardStepLayout>
    );
  }

  if (!application) {
    return (
      <WizardStepLayout currentStep={1}>
        <div className="flex flex-col items-center justify-center text-center py-12">
          <p className="text-muted-foreground mb-4">Application not found</p>
          <Link to="/dashboard">
            <Button variant="outline">Back to Dashboard</Button>
          </Link>
        </div>
      </WizardStepLayout>
    );
  }

  const currentStep = STATUS_TO_STEP[application.status] || 1;

  const parsedKeywords = (() => {
    if (!application.keywords) return null;
    try {
      return JSON.parse(application.keywords) as { text: string }[];
    } catch {
      return null;
    }
  })();

  return (
    <WizardStepLayout currentStep={currentStep}>
      <Link
        to="/dashboard"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to Dashboard
      </Link>

      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-fluid-3xl font-bold">{application.company_name}</h1>
            <p className="text-muted-foreground">
              <span title={application.created_at}>
                Created {formatDistanceToNow(new Date(application.created_at))} ago
              </span>
              {application.updated_at !== application.created_at && (
                <>
                  {' '}&bull;{' '}
                  <span title={application.updated_at}>
                    Updated {formatDistanceToNow(new Date(application.updated_at))} ago
                  </span>
                </>
              )}
            </p>
          </div>
          <ApplicationStatusBadge status={application.status} />
        </div>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Job Posting</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap">{application.job_posting}</p>
            {application.job_url && (
              <a
                href={application.job_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline mt-4 inline-block"
              >
                View original posting &rarr;
              </a>
            )}
          </CardContent>
        </Card>

        {parsedKeywords && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Keywords</CardTitle>
                <Link
                  to={`/applications/${id}/keywords`}
                  className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  <ListChecks className="h-4 w-4" aria-hidden="true" />
                  View Keywords
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {parsedKeywords.map((k) => (
                  <span
                    key={k.text}
                    className="px-3 py-1 bg-accent rounded-full text-sm"
                  >
                    {k.text}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {!parsedKeywords && (
        <Link
          to={`/applications/${id}/keywords`}
          className="inline-flex items-center gap-1 text-sm text-primary hover:underline mt-4"
        >
          <ListChecks className="h-4 w-4" aria-hidden="true" />
          View Keywords
        </Link>
      )}

      {!['sent', 'callback', 'offer', 'closed'].includes(application.status) && (
        <div className="mt-8 flex justify-end">
          <Button onClick={handleContinue}>
            Continue Workflow
          </Button>
        </div>
      )}
    </WizardStepLayout>
  );
}
