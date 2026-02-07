import { useCallback } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { restrictToVerticalAxis } from '@dnd-kit/modifiers';
import { SortableKeywordItem } from './SortableKeywordItem';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import type { KeywordWithId } from '@/api/applications';

interface KeywordListProps {
  keywords: KeywordWithId[];
  onReorder: (keywords: KeywordWithId[]) => void;
}

export function KeywordList({ keywords, onReorder }: KeywordListProps) {
  const isMobile = useMediaQuery('(max-width: 768px)');

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;

      if (over && active.id !== over.id) {
        const oldIndex = keywords.findIndex((k) => k._id === active.id);
        const newIndex = keywords.findIndex((k) => k._id === over.id);
        const newKeywords = arrayMove(keywords, oldIndex, newIndex);
        onReorder(newKeywords);
      }
    },
    [keywords, onReorder],
  );

  const handleMoveUp = useCallback(
    (index: number) => {
      if (index === 0) return;
      const newKeywords = arrayMove(keywords, index, index - 1);
      onReorder(newKeywords);
    },
    [keywords, onReorder],
  );

  const handleMoveDown = useCallback(
    (index: number) => {
      if (index === keywords.length - 1) return;
      const newKeywords = arrayMove(keywords, index, index + 1);
      onReorder(newKeywords);
    },
    [keywords, onReorder],
  );

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      modifiers={[restrictToVerticalAxis]}
      onDragEnd={handleDragEnd}
    >
      <SortableContext
        items={keywords.map((k) => k._id)}
        strategy={verticalListSortingStrategy}
      >
        <div role="list" className="space-y-3">
          {keywords.map((keyword, index) => (
            <SortableKeywordItem
              key={keyword._id}
              keyword={keyword}
              index={index}
              isFirst={index === 0}
              isLast={index === keywords.length - 1}
              isMobile={isMobile}
              onMoveUp={() => handleMoveUp(index)}
              onMoveDown={() => handleMoveDown(index)}
            />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}
