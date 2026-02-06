import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { Keyword } from '@/api/applications';

interface KeywordListProps {
  keywords: Keyword[];
  onReorder?: (keywords: Keyword[]) => void;
}

const priorityColors: Record<number, string> = {
  10: 'bg-red-500 text-white',
  9: 'bg-red-400 text-white',
  8: 'bg-orange-500 text-white',
  7: 'bg-orange-400 text-white',
  6: 'bg-yellow-500 text-black',
  5: 'bg-yellow-400 text-black',
  4: 'bg-green-400 text-white',
  3: 'bg-green-300 text-black',
  2: 'bg-blue-300 text-black',
  1: 'bg-gray-300 text-black',
};

const categoryColors: Record<string, string> = {
  technical_skill: 'bg-blue-100 text-blue-800',
  soft_skill: 'bg-purple-100 text-purple-800',
  experience: 'bg-green-100 text-green-800',
  qualification: 'bg-yellow-100 text-yellow-800',
  tool: 'bg-orange-100 text-orange-800',
  domain: 'bg-pink-100 text-pink-800',
  general: 'bg-gray-100 text-gray-800',
};

export function KeywordList({ keywords }: KeywordListProps) {
  return (
    <div role="list" className="space-y-3">
      {keywords.map((keyword, index) => (
        <div
          key={keyword.text}
          role="listitem"
          className="flex items-center gap-4 p-4 bg-card rounded-lg border min-h-[44px]"
        >
          <span className="text-muted-foreground w-6 text-center" aria-hidden="true">
            {index + 1}
          </span>

          <div className="flex-1 flex items-center gap-2 flex-wrap">
            <span className="font-medium">{keyword.text}</span>
            <Badge
              variant="outline"
              className={cn('text-xs', categoryColors[keyword.category] || categoryColors.general)}
            >
              {keyword.category.replace(/_/g, ' ')}
            </Badge>
          </div>

          <div
            className={cn(
              'px-3 py-1 rounded-full text-sm font-medium min-w-[44px] text-center',
              priorityColors[keyword.priority] || 'bg-gray-200',
            )}
            aria-label={`Priority ${keyword.priority} out of 10`}
          >
            {keyword.priority}
          </div>
        </div>
      ))}
    </div>
  );
}
