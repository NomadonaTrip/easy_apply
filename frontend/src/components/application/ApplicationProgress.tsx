import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ApplicationStatus } from './ApplicationStatusBadge';

interface ApplicationProgressProps {
  currentStatus: ApplicationStatus;
  onStepClick?: (status: ApplicationStatus) => void;
}

const workflowSteps: ApplicationStatus[] = [
  'created',
  'keywords',
  'researching',
  'reviewed',
  'exported',
  'sent',
];

const stepLabels: Record<string, string> = {
  created: 'Create',
  keywords: 'Keywords',
  researching: 'Research',
  reviewed: 'Review',
  exported: 'Export',
  sent: 'Send',
};

export function ApplicationProgress({
  currentStatus,
  onStepClick,
}: ApplicationProgressProps) {
  const currentIndex = workflowSteps.indexOf(currentStatus);

  // Handle outcome statuses
  const isFinalOutcome = ['callback', 'offer', 'closed'].includes(currentStatus);
  const effectiveIndex = isFinalOutcome ? workflowSteps.length : currentIndex;

  return (
    <nav aria-label="Application progress" className="flex items-center justify-between overflow-x-auto">
      {workflowSteps.map((step, index) => {
        const isComplete = index < effectiveIndex;
        const isCurrent = index === effectiveIndex && !isFinalOutcome;
        const isClickable = onStepClick && isComplete;

        return (
          <div key={step} className="flex items-center flex-shrink-0">
            <button
              onClick={() => isClickable && onStepClick(step)}
              disabled={!isClickable}
              aria-label={`${stepLabels[step]}${isComplete ? ' (completed)' : isCurrent ? ' (current)' : ''}`}
              className={cn(
                'flex flex-col items-center min-w-[44px]',
                isClickable && 'cursor-pointer hover:opacity-80',
              )}
            >
              <div
                aria-current={isCurrent ? 'step' : undefined}
                className={cn(
                  'w-10 h-10 rounded-full flex items-center justify-center',
                  isComplete && 'bg-primary text-primary-foreground',
                  isCurrent && 'bg-primary/20 border-2 border-primary',
                  !isComplete && !isCurrent && 'bg-muted',
                )}
              >
                {isComplete ? (
                  <Check className="w-5 h-5" data-testid="check-icon" />
                ) : (
                  <span className="text-sm font-medium">{index + 1}</span>
                )}
              </div>
              <span
                className={cn(
                  'mt-2 text-xs hidden sm:block',
                  isCurrent && 'font-medium text-primary',
                  isComplete && 'text-muted-foreground',
                )}
              >
                {stepLabels[step]}
              </span>
            </button>

            {/* Connector line */}
            {index < workflowSteps.length - 1 && (
              <div
                className={cn(
                  'h-0.5 w-6 sm:w-12 mx-1 sm:mx-2',
                  index < effectiveIndex ? 'bg-primary' : 'bg-muted',
                )}
              />
            )}
          </div>
        );
      })}
    </nav>
  );
}
