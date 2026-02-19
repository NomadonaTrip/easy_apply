import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAccomplishments } from '@/hooks/useExperience';
import { FileText, Briefcase } from 'lucide-react';

export function AccomplishmentsList() {
  const { data: accomplishments, isLoading, error } = useAccomplishments();

  if (isLoading) {
    return <div className="animate-pulse h-48 bg-muted rounded-md" />;
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-destructive">Failed to load accomplishments</p>
        </CardContent>
      </Card>
    );
  }

  if (!accomplishments || accomplishments.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-center">
          <p className="text-muted-foreground">
            No accomplishments extracted yet. Upload a resume to get started.
          </p>
        </CardContent>
      </Card>
    );
  }

  const getSourceLabel = (source: string | null) => {
    if (source === 'resume') {
      return 'From resume';
    }
    if (source === 'application') {
      return 'From application';
    }
    if (source === 'application-enriched') {
      return 'Enriched';
    }
    return null;
  };

  const getSourceIcon = (source: string | null) => {
    if (source === 'resume') {
      return <FileText className="h-4 w-4" />;
    }
    if (source === 'application' || source === 'application-enriched') {
      return <Briefcase className="h-4 w-4" />;
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Accomplishments</span>
          <Badge variant="secondary">{accomplishments.length} total</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-4">
          {accomplishments.map((accomplishment) => (
            <li
              key={accomplishment.id}
              className="border-l-2 border-primary/30 pl-4 py-2"
            >
              <p className="font-medium">{accomplishment.description}</p>
              {accomplishment.context && (
                <p className="text-sm text-muted-foreground mt-1">
                  {accomplishment.context}
                </p>
              )}
              {accomplishment.source && (
                <div className="flex items-center gap-1.5 mt-2">
                  {accomplishment.source === 'application-enriched' ? (
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 bg-primary/10 text-primary">
                      {getSourceIcon(accomplishment.source)}
                      {getSourceLabel(accomplishment.source)}
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                      {getSourceIcon(accomplishment.source)}
                      {getSourceLabel(accomplishment.source)}
                    </Badge>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
