import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertTriangle, CheckCircle, Info } from 'lucide-react';

interface ConstraintWarningsProps {
  violationsFixed: number;
  warnings: string[];
}

export function ConstraintWarnings({
  violationsFixed,
  warnings,
}: ConstraintWarningsProps) {
  if (violationsFixed === 0 && warnings.length === 0) {
    return (
      <Alert className="bg-success/5 border-success/30">
        <CheckCircle className="h-4 w-4 text-success" />
        <AlertTitle className="text-success-foreground">
          All constraints passed
        </AlertTitle>
        <AlertDescription className="text-success-foreground/80">
          No AI cliches or formatting issues detected.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-2">
      {violationsFixed > 0 && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>Auto-corrections applied</AlertTitle>
          <AlertDescription>
            {violationsFixed} formatting {violationsFixed === 1 ? 'issue was' : 'issues were'} automatically fixed
            (em-dashes, smart quotes).
          </AlertDescription>
        </Alert>
      )}

      {warnings.length > 0 && (
        <Alert className="border-warning/30 bg-warning/5">
          <AlertTriangle className="h-4 w-4 text-warning" />
          <AlertTitle className="text-warning-foreground">
            Review recommended
          </AlertTitle>
          <AlertDescription className="text-warning-foreground/80">
            <p className="mb-2">
              {warnings.length} potential {warnings.length === 1 ? 'issue' : 'issues'} detected. Consider reviewing:
            </p>
            <ul className="list-disc pl-4 space-y-1">
              {warnings.slice(0, 5).map((warning, i) => (
                <li key={i} className="text-sm">{warning}</li>
              ))}
              {warnings.length > 5 && (
                <li className="text-sm">
                  ... and {warnings.length - 5} more
                </li>
              )}
            </ul>
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
