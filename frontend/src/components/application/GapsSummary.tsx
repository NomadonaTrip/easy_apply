import { AlertTriangle, Info } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import type { ResearchResult, ResearchSourceResult } from '@/lib/parseResearch';

const CATEGORY_LABELS: Record<string, string> = {
  strategic_initiatives: 'Strategic Initiatives',
  competitive_landscape: 'Competitive Landscape',
  news_momentum: 'Recent News & Momentum',
  industry_context: 'Industry Context',
  culture_values: 'Culture & Values',
  leadership_direction: 'Leadership Direction',
};

const GAP_SUGGESTIONS: Record<string, string> = {
  strategic_initiatives:
    'Consider adding context from the job posting, company website, or recruiter conversations',
  competitive_landscape:
    'Check industry reports or the company blog for competitor mentions',
  news_momentum:
    'Look for recent press releases, funding announcements, or product launches',
  industry_context:
    'Add context from industry publications or the job description itself',
  culture_values:
    'Check the company careers page, Glassdoor reviews, or social media presence',
  leadership_direction:
    'Look for CEO interviews, conference talks, or company blog posts',
};

interface GapsSummaryProps {
  gaps: string[];
  research: ResearchResult;
  totalSources: number;
  onAddContext?: () => void;
}

export function GapsSummary({
  gaps,
  research,
  totalSources,
  onAddContext,
}: GapsSummaryProps) {
  if (gaps.length === 0) {
    return null;
  }

  return (
    <Alert className="border-warning/30 bg-warning/5">
      <AlertTriangle className="h-4 w-4 text-warning" />
      <AlertTitle className="text-warning-foreground">
        {gaps.length} of {totalSources} research categories with incomplete
        context
      </AlertTitle>
      <AlertDescription>
        <div className="space-y-3 mt-2">
          {/* Gap List */}
          <ul className="space-y-2 text-sm" role="list">
            {gaps.map((gap) => {
              const sourceData = research[
                gap as keyof ResearchResult
              ] as ResearchSourceResult | undefined;
              const reason =
                sourceData && typeof sourceData === 'object'
                  ? sourceData.reason
                  : null;

              return (
                <li key={gap} className="flex items-start gap-2">
                  <span className="font-medium text-warning-foreground min-w-[140px]">
                    {CATEGORY_LABELS[gap] || gap}:
                  </span>
                  <span className="text-warning-foreground/80">
                    {reason || 'Information not found'}
                    {GAP_SUGGESTIONS[gap] && (
                      <span className="block text-xs text-muted-foreground mt-0.5">
                        {GAP_SUGGESTIONS[gap]}
                      </span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>

          {/* Info Box */}
          <div className="flex items-start gap-2 p-3 bg-warning/10 rounded-lg">
            <Info
              className="h-4 w-4 text-warning-foreground mt-0.5 shrink-0"
              aria-hidden="true"
            />
            <div className="text-sm text-warning-foreground">
              <p className="font-medium">
                This won&apos;t block your application
              </p>
              <p className="mt-1 text-warning-foreground/80">
                Document generation will proceed with available information. You
                can optionally add context manually to fill these gaps.
              </p>
            </div>
          </div>

          {/* Action Button */}
          {onAddContext && (
            <Button
              variant="outline"
              size="sm"
              onClick={onAddContext}
              className="border-warning/30 text-warning-foreground hover:bg-warning/10"
            >
              Add Manual Context
            </Button>
          )}
        </div>
      </AlertDescription>
    </Alert>
  );
}
