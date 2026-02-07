import { Card, CardContent } from '@/components/ui/card';
import type { Application } from '@/api/applications';

interface StatsGridProps {
  applications: Application[];
}

export function StatsGrid({ applications }: StatsGridProps) {
  const totalSent = applications.filter((a) =>
    ['sent', 'callback', 'offer', 'closed'].includes(a.status),
  ).length;

  const callbacks = applications.filter((a) =>
    ['callback', 'offer'].includes(a.status),
  ).length;

  const callbackRate =
    totalSent > 0 ? `${Math.round((callbacks / totalSent) * 100)}%` : '\u2014';

  const stats = [
    { label: 'Total Sent', value: totalSent },
    { label: 'Callbacks', value: callbacks },
    { label: 'Callback Rate', value: callbackRate },
    { label: 'Avg Match', value: '\u2014' },
  ];

  return (
    <div className="flex overflow-x-auto snap-x snap-mandatory gap-3 lg:grid lg:grid-cols-4 lg:gap-4 lg:overflow-visible">
      {stats.map((stat) => (
        <Card key={stat.label} className="min-w-[140px] snap-start lg:min-w-0">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">{stat.label}</p>
            <p className="text-2xl font-bold text-primary">{stat.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
