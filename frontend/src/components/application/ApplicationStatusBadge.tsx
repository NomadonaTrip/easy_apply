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
    color: 'bg-gray-100 text-gray-800',
    description: 'Application created, awaiting keyword extraction',
  },
  keywords: {
    label: 'Keywords',
    color: 'bg-blue-100 text-blue-800',
    description: 'Keywords extracted, ready for research',
  },
  researching: {
    label: 'Researching',
    color: 'bg-yellow-100 text-yellow-800',
    description: 'Company research in progress',
  },
  reviewed: {
    label: 'Reviewed',
    color: 'bg-cyan-100 text-cyan-800',
    description: 'Research complete, ready for document generation',
  },
  exported: {
    label: 'Exported',
    color: 'bg-green-100 text-green-800',
    description: 'Documents generated and exported',
  },
  sent: {
    label: 'Sent',
    color: 'bg-teal-100 text-teal-800',
    description: 'Application submitted to company',
  },
  callback: {
    label: 'Callback',
    color: 'bg-emerald-100 text-emerald-800',
    description: 'Got interview or callback',
  },
  offer: {
    label: 'Offer',
    color: 'bg-amber-100 text-amber-800',
    description: 'Received job offer',
  },
  closed: {
    label: 'Closed',
    color: 'bg-red-100 text-red-800',
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
