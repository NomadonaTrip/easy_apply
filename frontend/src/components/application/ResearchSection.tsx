import { AlertTriangle, Lightbulb } from 'lucide-react';

interface ResearchSectionProps {
  content: string | null | undefined;
  reason: string | null | undefined;
  isGap: boolean;
  partial?: boolean | null;
  partialNote?: string | null;
}

export function ResearchSection({ content, reason, isGap, partial, partialNote }: ResearchSectionProps) {
  if (isGap || !content) {
    return (
      <div className="flex items-start gap-3 p-4 bg-warning/5 rounded-lg border border-warning/20">
        <AlertTriangle className="h-5 w-5 text-warning mt-0.5 shrink-0" aria-hidden="true" />
        <div>
          <p className="font-medium text-warning-foreground">Limited Information Available</p>
          <p className="text-sm text-warning-foreground/80 mt-1">
            {reason || "This information couldn't be found during research. You can add context manually if needed."}
          </p>
        </div>
      </div>
    );
  }

  // Extract key insights (lines starting with bullet markers or key phrases)
  const lines = content.split('\n').filter((l) => l.trim().length > 0);
  const keyInsights = lines.filter(
    (line) =>
      line.startsWith('•') ||
      line.startsWith('-') ||
      line.startsWith('*') ||
      /^\d+\./.test(line.trim()),
  );

  const remainingLines = lines.filter(
    (line) =>
      !(
        line.startsWith('•') ||
        line.startsWith('-') ||
        line.startsWith('*') ||
        /^\d+\./.test(line.trim())
      ),
  );
  const remainingContent = remainingLines.join('\n').trim();

  return (
    <div className="space-y-4 p-4">
      {/* Partial Information Warning */}
      {partial && (
        <div className="flex items-start gap-2 p-3 bg-warning/5 rounded-lg border border-warning/20">
          <AlertTriangle className="h-4 w-4 text-warning mt-0.5 shrink-0" aria-hidden="true" />
          <div className="text-sm">
            <p className="font-medium text-warning-foreground">Partial Information</p>
            <p className="text-warning-foreground/80 mt-1">
              {partialNote || 'Some information may be incomplete.'}
            </p>
          </div>
        </div>
      )}

      {/* Key Insights Box */}
      {keyInsights.length > 0 && (
        <div className="p-4 bg-primary/5 rounded-lg border border-primary/20">
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb className="h-4 w-4 text-primary" aria-hidden="true" />
            <p className="font-medium text-primary">Key Insights</p>
          </div>
          <ul className="space-y-1 text-sm">
            {keyInsights.slice(0, 5).map((insight, i) => (
              <li key={i} className="text-muted-foreground">
                {insight.replace(/^[-•*]\s*/, '').replace(/^\d+\.\s*/, '')}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Full Content */}
      <div className="prose prose-sm max-w-none">
        <div className="text-muted-foreground whitespace-pre-wrap leading-relaxed">
          {remainingContent || content}
        </div>
      </div>
    </div>
  );
}
