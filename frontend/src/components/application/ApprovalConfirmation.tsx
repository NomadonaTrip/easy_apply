import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Check, AlertTriangle, ArrowRight, Pencil, Loader2 } from 'lucide-react';

const CATEGORY_LABELS: Record<string, string> = {
  strategic_initiatives: 'Strategic Initiatives',
  competitive_landscape: 'Competitive Landscape',
  news_momentum: 'Recent News & Momentum',
  industry_context: 'Industry Context',
  culture_values: 'Culture & Values',
  leadership_direction: 'Leadership Direction',
};

interface ApprovalConfirmationProps {
  sourcesFound: number;
  gaps: string[];
  hasManualContext: boolean;
  onApprove: () => void;
  onAddContext: () => void;
  isApproving: boolean;
}

export function ApprovalConfirmation({
  sourcesFound,
  gaps,
  hasManualContext,
  onApprove,
  onAddContext,
  isApproving,
}: ApprovalConfirmationProps) {
  const hasGaps = gaps.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Ready to Generate Documents</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary Stats */}
        <div className="flex flex-wrap gap-4">
          <div className="p-4 bg-success/10 rounded-lg border border-success/20 flex-1 min-w-[140px]">
            <div className="flex items-center gap-2">
              <Check className="h-5 w-5 text-success" aria-hidden="true" />
              <span className="font-medium text-success">{sourcesFound} sources</span>
            </div>
            <p className="text-sm text-success/80 mt-1">Research data collected</p>
          </div>

          {hasGaps && (
            <div className="p-4 bg-warning/10 rounded-lg border border-warning/20 flex-1 min-w-[140px]">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-warning" aria-hidden="true" />
                <span className="font-medium text-warning">{gaps.length} {gaps.length === 1 ? 'gap' : 'gaps'}</span>
              </div>
              <p className="text-sm text-warning/80 mt-1">Will proceed without</p>
            </div>
          )}

          {hasManualContext && (
            <div className="p-4 bg-primary/10 rounded-lg border border-primary/20 flex-1 min-w-[140px]">
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-primary" aria-hidden="true" />
                <span className="font-medium text-primary">Context added</span>
              </div>
              <p className="text-sm text-primary/80 mt-1">Your input will be used</p>
            </div>
          )}
        </div>

        {/* Gap Acknowledgment */}
        {hasGaps && (
          <Alert className="border-warning/30 bg-warning/5">
            <AlertTriangle className="h-4 w-4 text-warning" />
            <AlertDescription>
              <p className="font-medium text-warning-foreground">
                Proceeding with limited research
              </p>
              <p className="text-sm mt-1 text-warning-foreground/80">
                The following categories had incomplete context:{' '}
                {gaps.map((g) => CATEGORY_LABELS[g] || g).join(', ')}.
                Your documents will be generated using available information.
              </p>
              <Button
                variant="link"
                size="sm"
                className="p-0 h-auto mt-2 text-warning-foreground"
                onClick={onAddContext}
              >
                <Pencil className="h-3 w-3 mr-1" aria-hidden="true" />
                Add manual context to fill gaps
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Pre-approval Checklist */}
        <div className="text-sm text-muted-foreground space-y-1">
          <p>By continuing, you confirm:</p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>You've reviewed the research summary</li>
            <li>The company information looks accurate</li>
            {hasGaps && <li>You accept proceeding with research gaps</li>}
          </ul>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button variant="outline" onClick={onAddContext}>
            <Pencil className="h-4 w-4 mr-2" aria-hidden="true" />
            {hasManualContext ? 'Edit Context' : 'Add Context'}
          </Button>
          <Button
            onClick={onApprove}
            disabled={isApproving}
            size="lg"
          >
            {isApproving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" aria-hidden="true" />
                Approving...
              </>
            ) : (
              <>
                Continue to Generation
                <ArrowRight className="h-4 w-4 ml-2" aria-hidden="true" />
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
