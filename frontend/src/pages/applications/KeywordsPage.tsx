import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { KeywordList } from '@/components/application/KeywordList';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useSaveKeywords } from '@/hooks/useKeywords';
import { getApplication } from '@/api/applications';
import type { Keyword, KeywordWithId } from '@/api/applications';
import { WizardStepLayout } from '@/components/layout/WizardStepLayout';
import { Loader2, Check } from 'lucide-react';

export function KeywordsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [localKeywords, setLocalKeywords] = useState<KeywordWithId[]>([]);
  const [hasSaved, setHasSaved] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const { data: application, isLoading, isError } = useQuery({
    queryKey: ['application', id],
    queryFn: () => getApplication(Number(id)),
  });

  const { save, isSaving, error } = useSaveKeywords(id!);

  // Initialize local state from server data (once, during render)
  if (application?.keywords && !initialized) {
    try {
      const parsed: Keyword[] = JSON.parse(application.keywords);
      setLocalKeywords(
        parsed.map((k, i) => ({ ...k, _id: `kw-${i}` })),
      );
      setInitialized(true);
    } catch {
      // Corrupted data fallback
    }
  }

  const handleReorder = (newKeywords: KeywordWithId[]) => {
    setLocalKeywords(newKeywords);
    save(newKeywords.map(({ text, priority, category }) => ({ text, priority, category })));
    setHasSaved(true);
  };

  const handleContinue = () => {
    navigate(`/applications/${id}/research`);
  };

  if (isLoading) {
    return (
      <WizardStepLayout currentStep={2}>
        <Skeleton className="h-8 w-48 mb-6" />
        <div className="space-y-4">
          {Array.from({ length: 10 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </WizardStepLayout>
    );
  }

  if (isError) {
    return (
      <WizardStepLayout currentStep={2}>
        <p className="text-destructive">Failed to load application data</p>
      </WizardStepLayout>
    );
  }

  return (
    <WizardStepLayout currentStep={2}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-fluid-2xl font-bold">Keywords</h1>
          <p className="text-muted-foreground">
            Drag to reorder. Higher priority keywords will be emphasized more.
          </p>
        </div>

        {/* Save status indicator */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          {isSaving ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Saving...
            </>
          ) : hasSaved ? (
            <>
              <Check className="h-4 w-4 text-green-500" /> Saved
            </>
          ) : null}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-destructive/10 text-destructive rounded-md">
          Failed to save keyword order. Please try again.
        </div>
      )}

      <Card className="shadow-md">
        <CardContent className="p-4 lg:p-6">
          {localKeywords.length > 0 ? (
            <KeywordList keywords={localKeywords} onReorder={handleReorder} />
          ) : (
            <p className="text-muted-foreground">No keywords extracted yet.</p>
          )}
        </CardContent>
      </Card>

      <div className="mt-8 flex justify-between">
        <Button
          variant="ghost"
          onClick={() => navigate(`/applications/${id}`)}
        >
          Back
        </Button>
        <Button
          onClick={handleContinue}
          disabled={isSaving}
          className="min-h-[44px]"
        >
          Start Research
        </Button>
      </div>
    </WizardStepLayout>
  );
}
