import { cn } from '@/lib/utils';
import { Check, AlertTriangle, Loader2, Circle } from 'lucide-react';
import type { ResearchSourceStatus } from '@/hooks/useResearchStream';

interface ResearchSourceItemProps {
  label: string;
  status: ResearchSourceStatus;
  message?: string;
  found?: boolean;
}

const icons: Record<ResearchSourceStatus, (found?: boolean) => React.ReactNode> = {
  pending: () => <Circle className="h-5 w-5 text-muted-foreground" aria-hidden="true" />,
  running: () => <Loader2 className="h-5 w-5 text-primary animate-spin" aria-label="Loading" />,
  complete: (found) =>
    found !== false ? (
      <Check className="h-5 w-5 text-green-600" aria-hidden="true" />
    ) : (
      <AlertTriangle className="h-5 w-5 text-yellow-600" aria-hidden="true" />
    ),
  failed: () => <AlertTriangle className="h-5 w-5 text-yellow-600" aria-hidden="true" />,
};

function getStatusText(status: ResearchSourceStatus, message?: string, found?: boolean): string {
  switch (status) {
    case 'pending':
      return 'Waiting...';
    case 'running':
      return message || 'Researching...';
    case 'complete':
      return found !== false ? 'Complete' : 'Limited info';
    case 'failed':
      return 'Not found';
  }
}

export function ResearchSourceItem({ label, status, message, found }: ResearchSourceItemProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-4 p-4 rounded-lg border transition-colors',
        status === 'running' && 'bg-primary/5 border-primary/20',
        status === 'complete' && found !== false && 'bg-green-50 border-green-200 dark:bg-green-950/20 dark:border-green-900',
        ((status === 'complete' && found === false) || status === 'failed') &&
          'bg-yellow-50 border-yellow-200 dark:bg-yellow-950/20 dark:border-yellow-900',
        status === 'pending' && 'bg-muted/30',
      )}
    >
      {icons[status](found)}

      <div className="flex-1 min-w-0">
        <p className={cn('font-medium', status === 'pending' && 'text-muted-foreground')}>{label}</p>
        <p className="text-sm text-muted-foreground truncate">{getStatusText(status, message, found)}</p>
      </div>
    </div>
  );
}
