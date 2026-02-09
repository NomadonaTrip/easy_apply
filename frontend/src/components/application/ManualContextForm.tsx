import { useState } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Lightbulb, Save, X } from 'lucide-react';

interface ManualContextFormProps {
  initialValue?: string;
  gaps: string[];
  onSave: (context: string) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const GAP_PROMPTS: Record<string, string> = {
  strategic_initiatives:
    'What the company is building, expanding, or transforming - any strategic bets or priorities',
  competitive_landscape:
    'Main competitors, how they differentiate, market position',
  news_momentum:
    'Recent announcements, funding, product launches, partnerships in the last 6-12 months',
  industry_context:
    'Market trends, regulatory shifts, or challenges affecting the company\'s industry',
  culture_values:
    'Work environment, values, how the company describes itself, team dynamics',
  leadership_direction:
    'CEO/executive vision, strategic direction, leadership background that signals priorities',
};

const MAX_LENGTH = 5000;

export function ManualContextForm({
  initialValue = '',
  gaps,
  onSave,
  onCancel,
  isLoading,
}: ManualContextFormProps) {
  const [context, setContext] = useState(initialValue);

  const handleSave = () => {
    onSave(context.trim());
  };

  const remainingChars = MAX_LENGTH - context.length;

  return (
    <div className="space-y-6">
      {/* Helpful Prompts Based on Gaps */}
      {gaps.length > 0 && (
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Lightbulb className="h-4 w-4" aria-hidden="true" />
              Suggestions Based on Missing Information
            </CardTitle>
            <CardDescription>
              These areas couldn&apos;t be found during research. Any info you
              can provide will help.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm" role="list">
              {gaps.map((gap) => (
                <li key={gap} className="flex gap-2">
                  <span className="font-medium text-primary capitalize">
                    {gap.replace(/_/g, ' ')}:
                  </span>
                  <span className="text-muted-foreground">
                    {GAP_PROMPTS[gap] || 'Any relevant details'}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Context Input */}
      <div className="space-y-2">
        <Label htmlFor="manual-context">Additional Context</Label>
        <Textarea
          id="manual-context"
          placeholder={`Enter any additional information about the company that would help tailor your application...\n\nFor example:\n- Information from your network about the company culture\n- Details from an informational interview\n- Specific projects or initiatives you know about\n- Why you're excited about this specific role`}
          value={context}
          onChange={(e) => setContext(e.target.value)}
          className="min-h-[200px] resize-y"
          maxLength={MAX_LENGTH}
          aria-describedby="context-char-count"
        />
        <div
          id="context-char-count"
          className="flex justify-between text-sm text-muted-foreground"
        >
          <span>
            {remainingChars < 500 && (
              <span
                className={
                  remainingChars < 100 ? 'text-destructive' : 'text-warning'
                }
              >
                {remainingChars} characters remaining
              </span>
            )}
          </span>
          <span>
            {context.length} / {MAX_LENGTH}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={onCancel} disabled={isLoading}>
          <X className="h-4 w-4 mr-2" aria-hidden="true" />
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={isLoading}>
          <Save className="h-4 w-4 mr-2" aria-hidden="true" />
          {isLoading ? 'Saving...' : 'Save Context'}
        </Button>
      </div>
    </div>
  );
}
