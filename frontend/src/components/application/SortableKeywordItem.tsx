import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, ChevronUp, ChevronDown } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { KeywordWithId } from '@/api/applications';

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
  soft_skill: 'bg-cyan-100 text-cyan-800',
  experience: 'bg-green-100 text-green-800',
  qualification: 'bg-yellow-100 text-yellow-800',
  tool: 'bg-orange-100 text-orange-800',
  domain: 'bg-pink-100 text-pink-800',
  general: 'bg-gray-100 text-gray-800',
};

interface SortableKeywordItemProps {
  keyword: KeywordWithId;
  index: number;
  isFirst: boolean;
  isLast: boolean;
  isMobile: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

export function SortableKeywordItem({
  keyword,
  index,
  isFirst,
  isLast,
  isMobile,
  onMoveUp,
  onMoveDown,
}: SortableKeywordItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: keyword._id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      role="listitem"
      className={cn(
        'flex items-center gap-4 p-4 bg-card rounded-lg border min-h-[44px]',
        isDragging && 'opacity-50 shadow-lg',
      )}
    >
      {/* Drag handle (desktop only) */}
      {!isMobile && (
        <button
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing touch-none"
          aria-label="Drag to reorder"
        >
          <GripVertical className="h-5 w-5 text-muted-foreground" />
        </button>
      )}

      {/* Mobile up/down buttons */}
      {isMobile && (
        <div className="flex flex-col gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={onMoveUp}
            disabled={isFirst}
            aria-label="Move up"
            className="h-11 w-11 p-0"
          >
            <ChevronUp className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={onMoveDown}
            disabled={isLast}
            aria-label="Move down"
            className="h-11 w-11 p-0"
          >
            <ChevronDown className="h-4 w-4" />
          </Button>
        </div>
      )}

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
  );
}
