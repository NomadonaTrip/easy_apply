import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { ApplicationStatusBadge } from '@/components/application/ApplicationStatusBadge';
import { formatDistanceToNow } from 'date-fns';
import type { Application } from '@/api/applications';

interface ApplicationCardProps {
  application: Application;
}

export function ApplicationCard({ application }: ApplicationCardProps) {
  return (
    <Link to={`/applications/${application.id}`}>
      <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">{application.company_name}</h3>
              <p className="text-sm text-muted-foreground" title={application.updated_at}>
                {formatDistanceToNow(new Date(application.updated_at))} ago
              </p>
            </div>
            <ApplicationStatusBadge status={application.status} />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
