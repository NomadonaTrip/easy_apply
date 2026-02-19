import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  useEnrichmentCandidates,
  useAcceptCandidate,
  useDismissCandidate,
  useBulkResolve,
} from '@/hooks/useExperience';
import type { EnrichmentCandidate } from '@/api/experience';
import { Check, X, AlertCircle, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

export function EnrichmentSuggestions() {
  const { data, isLoading, error, refetch } = useEnrichmentCandidates();
  const acceptMutation = useAcceptCandidate();
  const dismissMutation = useDismissCandidate();
  const bulkMutation = useBulkResolve();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-2 flex-1">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-5 w-64" />
              </div>
              <div className="flex gap-2">
                <Skeleton className="h-8 w-8" />
                <Skeleton className="h-8 w-8" />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <span>Failed to load enrichment suggestions.</span>
          <Button variant="ghost" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (!data || data.total_pending === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-center">
          <p className="text-muted-foreground">
            Your experience database is up to date.
          </p>
        </CardContent>
      </Card>
    );
  }

  const handleAccept = (candidate: EnrichmentCandidate) => {
    acceptMutation.mutate(candidate.id, {
      onSuccess: () => {
        toast.success('Suggestion accepted', {
          description: candidate.name,
        });
      },
      onError: (err) => {
        toast.error('Failed to accept', {
          description: err instanceof Error ? err.message : 'Please try again.',
        });
      },
    });
  };

  const handleDismiss = (candidate: EnrichmentCandidate) => {
    dismissMutation.mutate(candidate.id, {
      onSuccess: () => {
        toast.success('Suggestion dismissed');
      },
      onError: (err) => {
        toast.error('Failed to dismiss', {
          description: err instanceof Error ? err.message : 'Please try again.',
        });
      },
    });
  };

  const handleBulkAccept = (candidates: EnrichmentCandidate[]) => {
    bulkMutation.mutate(
      { ids: candidates.map((c) => c.id), action: 'accept' },
      {
        onSuccess: (result) => {
          toast.success(`${result.resolved} suggestions accepted`);
        },
        onError: (err) => {
          toast.error('Bulk accept failed', {
            description: err instanceof Error ? err.message : 'Please try again.',
          });
        },
      },
    );
  };

  const handleBulkDismiss = (candidates: EnrichmentCandidate[]) => {
    bulkMutation.mutate(
      { ids: candidates.map((c) => c.id), action: 'dismiss' },
      {
        onSuccess: (result) => {
          toast.success(`${result.resolved} suggestions dismissed`);
        },
        onError: (err) => {
          toast.error('Bulk dismiss failed', {
            description: err instanceof Error ? err.message : 'Please try again.',
          });
        },
      },
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">
          Suggestions ({data.total_pending} pending)
        </h3>
      </div>

      {Object.entries(data.candidates).map(([appId, group]) => {
        const { company_name, candidates } = group;
        const docTypes = [...new Set(candidates.map((c) => c.document_type))];

        return (
          <Card key={appId}>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <span>{company_name}</span>
                {docTypes.map((dt) => (
                  <Badge key={dt} variant="outline" className="text-xs font-normal">
                    {dt === 'cover_letter' ? 'Cover Letter' : 'Resume'}
                  </Badge>
                ))}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {candidates.map((candidate) => (
                <div
                  key={candidate.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <Badge
                      variant={candidate.candidate_type === 'skill' ? 'default' : 'secondary'}
                    >
                      {candidate.candidate_type === 'skill' ? 'Skill' : 'Accomplishment'}
                    </Badge>
                    <div className="min-w-0">
                      <p className="font-medium truncate">{candidate.name}</p>
                      {candidate.context && (
                        <p className="text-sm text-muted-foreground truncate">
                          {candidate.context}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1 ml-2 shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-primary hover:text-primary"
                      onClick={() => handleAccept(candidate)}
                      disabled={acceptMutation.isPending && acceptMutation.variables === candidate.id}
                      aria-label={`Accept ${candidate.name}`}
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      onClick={() => handleDismiss(candidate)}
                      disabled={dismissMutation.isPending && dismissMutation.variables === candidate.id}
                      aria-label={`Dismiss ${candidate.name}`}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}

              <div className="flex gap-2 pt-2 border-t">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleBulkAccept(candidates)}
                  disabled={bulkMutation.isPending}
                >
                  Accept All ({candidates.length})
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleBulkDismiss(candidates)}
                  disabled={bulkMutation.isPending}
                >
                  Dismiss All ({candidates.length})
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
