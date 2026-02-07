import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ApplicationStatusBadge } from '@/components/application/ApplicationStatusBadge';
import { ApplicationCard } from './ApplicationCard';
import { formatDistanceToNow } from 'date-fns';
import type { Application } from '@/api/applications';

interface ApplicationTableProps {
  applications: Application[];
}

type SortKey = 'company_name' | 'status' | 'updated_at';
type SortDir = 'asc' | 'desc';

export function ApplicationTable({ applications }: ApplicationTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('updated_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const sorted = [...applications].sort((a, b) => {
    const mul = sortDir === 'asc' ? 1 : -1;
    if (sortKey === 'updated_at') {
      return mul * (new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime());
    }
    return mul * String(a[sortKey]).localeCompare(String(b[sortKey]));
  });

  const headerClass =
    'px-4 py-3 text-left text-sm font-semibold text-muted-foreground cursor-pointer select-none hover:text-foreground transition-colors';

  return (
    <>
      {/* Desktop: table */}
      <div className="hidden lg:block rounded-lg border overflow-hidden">
        <table className="w-full">
          <thead className="bg-secondary">
            <tr>
              <th className={headerClass} onClick={() => handleSort('company_name')}>
                Company {sortKey === 'company_name' && (sortDir === 'asc' ? '\u2191' : '\u2193')}
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-muted-foreground">
                Match
              </th>
              <th className={headerClass} onClick={() => handleSort('status')}>
                Status {sortKey === 'status' && (sortDir === 'asc' ? '\u2191' : '\u2193')}
              </th>
              <th className={headerClass} onClick={() => handleSort('updated_at')}>
                Date {sortKey === 'updated_at' && (sortDir === 'asc' ? '\u2191' : '\u2193')}
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-muted-foreground">
                Action
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((app) => (
              <tr
                key={app.id}
                className="border-t hover:bg-secondary/50 transition-colors"
              >
                <td className="px-4 py-3 text-sm font-medium">{app.company_name}</td>
                <td className="px-4 py-3 text-sm text-muted-foreground">{'\u2014'}</td>
                <td className="px-4 py-3">
                  <ApplicationStatusBadge status={app.status} />
                </td>
                <td className="px-4 py-3 text-sm text-muted-foreground" title={app.updated_at}>
                  {formatDistanceToNow(new Date(app.updated_at))} ago
                </td>
                <td className="px-4 py-3">
                  <Link
                    to={`/applications/${app.id}`}
                    className="text-sm text-primary hover:underline"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile: stacked cards */}
      <div className="lg:hidden grid gap-3">
        {sorted.map((app) => (
          <ApplicationCard key={app.id} application={app} />
        ))}
      </div>
    </>
  );
}
