import { Progress } from '@/components/ui/progress';
import { ResearchSourceItem } from './ResearchSourceItem';
import { RESEARCH_CATEGORIES, type ResearchSourceState } from '@/hooks/useResearchStream';

const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(
  RESEARCH_CATEGORIES.map(({ source, label }): [string, string] => [source, label]),
);

interface ResearchProgressProps {
  sources: ResearchSourceState[];
  progress: number;
  isComplete: boolean;
}

export function ResearchProgress({ sources, progress, isComplete }: ResearchProgressProps) {
  const completedCount = sources.filter((s) => s.status === 'complete' || s.status === 'failed').length;
  const totalCount = sources.length;

  return (
    <div className="space-y-6">
      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Research Progress</span>
          <span className="font-medium">
            {completedCount}/{totalCount} categories
          </span>
        </div>
        <Progress
          value={progress}
          className="h-2"
          aria-label={`Research progress: ${completedCount} of ${totalCount} categories complete`}
        />
      </div>

      {/* Source List */}
      <div className="space-y-3">
        {sources.map((source) => (
          <ResearchSourceItem
            key={source.source}
            label={CATEGORY_LABELS[source.source] || source.source}
            status={source.status}
            message={source.message}
            found={source.found}
          />
        ))}
      </div>

      {/* Summary */}
      {isComplete && sources.filter((s) => s.status === 'failed').length > 0 && (
        <p className="text-sm text-muted-foreground">
          Note: Some sources had limited information available. This is normal and won't affect document generation.
        </p>
      )}
    </div>
  );
}
