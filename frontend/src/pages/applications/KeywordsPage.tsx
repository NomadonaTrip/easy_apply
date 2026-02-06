import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { KeywordList } from '@/components/application/KeywordList';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { getApplication } from '@/api/applications';
import type { Keyword } from '@/api/applications';

export function KeywordsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: application, isLoading, isError } = useQuery({
    queryKey: ['application', id],
    queryFn: () => getApplication(Number(id)),
  });

  let keywords: Keyword[] = [];
  if (application?.keywords) {
    try {
      keywords = JSON.parse(application.keywords);
    } catch {
      // Corrupted data fallback - keywords will remain empty array
    }
  }

  const handleContinue = () => {
    navigate(`/applications/${id}/research`);
  };

  if (isLoading) {
    return (
      <div className="container max-w-3xl py-8" aria-busy="true">
        <Skeleton className="h-8 w-48 mb-6" />
        <div className="space-y-4">
          {Array.from({ length: 10 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="container max-w-3xl py-8">
        <p className="text-destructive">Failed to load application data</p>
      </div>
    );
  }

  return (
    <div className="container max-w-3xl py-8">
      <h1 className="text-2xl font-bold mb-2">Keywords</h1>
      <p className="text-muted-foreground mb-6">
        Review keyword priorities. Higher priority keywords will be emphasized more in your resume.
      </p>

      {keywords.length > 0 ? (
        <KeywordList keywords={keywords} />
      ) : (
        <p className="text-muted-foreground">No keywords extracted yet.</p>
      )}

      <div className="mt-8 flex justify-end">
        <Button onClick={handleContinue} className="min-h-[44px]">
          Continue to Research
        </Button>
      </div>
    </div>
  );
}
