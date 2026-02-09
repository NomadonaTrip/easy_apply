import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { ResearchSection } from './ResearchSection';
import { GapsSummary } from './GapsSummary';
import { Rocket, Target, Newspaper, TrendingUp, Heart, Compass } from 'lucide-react';
import type { ResearchResult, ResearchSourceResult } from '@/lib/parseResearch';

const SECTION_CONFIG = [
  {
    key: 'strategic_initiatives' as const,
    label: 'Strategic Initiatives',
    icon: Rocket,
    description: 'What the company is building, expanding, or transforming',
  },
  {
    key: 'competitive_landscape' as const,
    label: 'Competitive Landscape',
    icon: Target,
    description: 'Market position, competitors, and differentiation',
  },
  {
    key: 'news_momentum' as const,
    label: 'Recent News & Momentum',
    icon: Newspaper,
    description: 'Product launches, funding, partnerships in last 6-12 months',
  },
  {
    key: 'industry_context' as const,
    label: 'Industry Context',
    icon: TrendingUp,
    description: 'Market trends, regulations, and challenges',
  },
  {
    key: 'culture_values' as const,
    label: 'Culture & Values',
    icon: Heart,
    description: 'How the company describes itself and what it values',
  },
  {
    key: 'leadership_direction' as const,
    label: 'Leadership Direction',
    icon: Compass,
    description: 'Strategic vision from public statements and talks',
  },
] as const;

interface ResearchSummaryProps {
  research: ResearchResult;
  gaps: string[];
  onAddContext?: () => void;
}

export function ResearchSummary({ research, gaps, onAddContext }: ResearchSummaryProps) {
  const foundCount = SECTION_CONFIG.length - gaps.length;

  return (
    <div className="space-y-6">
      {/* Gaps Alert - Show prominently when gaps exist */}
      {gaps.length > 0 && (
        <GapsSummary
          gaps={gaps}
          research={research}
          totalSources={SECTION_CONFIG.length}
          onAddContext={onAddContext}
        />
      )}

      {/* Synthesis */}
      {research.synthesis && (
        <div className="p-4 bg-primary/5 rounded-lg border border-primary/20">
          <p className="font-medium text-primary mb-2">Strategic Summary</p>
          <p className="text-muted-foreground leading-relaxed">{research.synthesis}</p>
        </div>
      )}

      {/* Summary Stats */}
      <div className="flex gap-4 p-4 bg-muted/50 rounded-lg">
        <div>
          <p className="text-2xl font-bold text-success">{foundCount}</p>
          <p className="text-sm text-muted-foreground">Sources found</p>
        </div>
        {gaps.length > 0 && (
          <div>
            <p className="text-2xl font-bold text-warning">{gaps.length}</p>
            <p className="text-sm text-muted-foreground">Gaps (non-blocking)</p>
          </div>
        )}
      </div>

      {/* Accordion Sections */}
      <Accordion type="single" collapsible className="w-full">
        {SECTION_CONFIG.map((config) => {
          const data = research[config.key] as ResearchSourceResult | undefined;
          const isGap = gaps.includes(config.key);
          const isPartial = data?.partial === true;
          const Icon = config.icon;

          return (
            <AccordionItem key={config.key} value={config.key}>
              <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-3">
                  <div
                    className={`p-2 rounded-lg ${isGap || isPartial ? 'bg-warning/10' : 'bg-primary/10'}`}
                  >
                    <Icon
                      className={`h-5 w-5 ${isGap || isPartial ? 'text-warning' : 'text-primary'}`}
                      aria-hidden="true"
                    />
                  </div>
                  <div className="text-left">
                    <p className="font-medium flex items-center gap-2">
                      {config.label}
                      {isGap && (
                        <span className="text-xs bg-warning/10 text-warning-foreground px-2 py-0.5 rounded">
                          Limited Info
                        </span>
                      )}
                      {isPartial && !isGap && (
                        <span className="text-xs bg-warning/10 text-warning-foreground px-2 py-0.5 rounded">
                          Partial
                        </span>
                      )}
                    </p>
                    <p className="text-sm text-muted-foreground">{config.description}</p>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <ResearchSection
                  content={data?.content ?? null}
                  reason={data?.reason ?? null}
                  isGap={isGap}
                  partial={data?.partial}
                  partialNote={data?.partial_note}
                />
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </div>
  );
}
