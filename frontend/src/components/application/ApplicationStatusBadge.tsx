import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { ApplicationStatus } from '@/api/applications';

export type { ApplicationStatus };

interface ApplicationStatusBadgeProps {
  status: ApplicationStatus;
  showTooltip?: boolean;
}

const statusConfig: Record<ApplicationStatus, {
  label: string;
  color: string;
  description: string;
}> = {
  created: {
    label: 'Created',
    color: 'bg-status-created text-status-created-foreground',
    description: 'Application created, awaiting keyword extraction',
  },
  keywords: {
    label: 'Keywords',
    color: 'bg-status-keywords text-status-keywords-foreground',
    description: 'Keywords extracted, ready for research',
  },
  researching: {
    label: 'Researching',
    color: 'bg-status-researching text-status-researching-foreground',
    description: 'Company research in progress',
  },
  reviewed: {
    label: 'Reviewed',
    color: 'bg-status-reviewed text-status-reviewed-foreground',
    description: 'Research complete, ready for document generation',
  },
  generating: {
    label: 'Generating',
    color: 'bg-status-generating text-status-generating-foreground',
    description: 'Documents being generated',
  },
  exported: {
    label: 'Exported',
    color: 'bg-status-exported text-status-exported-foreground',
    description: 'Documents generated and exported',
  },
  sent: {
    label: 'Sent',
    color: 'bg-status-sent text-status-sent-foreground',
    description: 'Application submitted to company',
  },
  callback: {
    label: 'Callback',
    color: 'bg-status-callback text-status-callback-foreground',
    description: 'Got interview or callback',
  },
  offer: {
    label: 'Offer',
    color: 'bg-status-offer text-status-offer-foreground',
    description: 'Received job offer',
  },
  closed: {
    label: 'Closed',
    color: 'bg-status-closed text-status-closed-foreground',
    description: 'Application closed',
  },
};

export function ApplicationStatusBadge({
  status,
  showTooltip = true,
}: ApplicationStatusBadgeProps) {
  const config = statusConfig[status];

  const badge = (
    <Badge className={cn('font-medium', config.color)}>
      {config.label}
    </Badge>
  );

  if (!showTooltip) return badge;

  return (
    <Tooltip>
      <TooltipTrigger asChild>{badge}</TooltipTrigger>
      <TooltipContent>
        <p>{config.description}</p>
      </TooltipContent>
    </Tooltip>
  );
}
