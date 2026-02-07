import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ApplicationStatusBadge } from '@/components/application/ApplicationStatusBadge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { WizardStepLayout } from '@/components/layout/WizardStepLayout';
import { formatDistanceToNow } from 'date-fns';
import { getApplication } from '@/api/applications';
import type { ApplicationStatus } from '@/api/applications';

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
    return <div>Loading...</div>;
  }

  if (!application) {
    return <div>Application not found</div>;
  }

  const currentStep = STATUS_TO_STEP[application.status] || 1;

  return (
    <WizardStepLayout currentStep={currentStep}>
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

        {application.keywords && (() => {
          try {
            const keywords: { text: string }[] = JSON.parse(application.keywords);
            return (
              <Card>
                <CardHeader>
                  <CardTitle>Keywords</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {keywords.map((k) => (
                      <span
                        key={k.text}
                        className="px-3 py-1 bg-primary/10 rounded-full text-sm"
                      >
                        {k.text}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          } catch {
            return null;
          }
        })()}
      </div>

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
