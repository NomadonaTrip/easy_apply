import { z } from 'zod/v4';

const ResearchSourceResultSchema = z.object({
  found: z.boolean(),
  content: z.string().nullable().optional(),
  reason: z.string().nullable().optional(),
  partial: z.boolean().nullable().optional(),
  partial_note: z.string().nullable().optional(),
});

const ResearchResultSchema = z.object({
  strategic_initiatives: ResearchSourceResultSchema.nullable().optional(),
  competitive_landscape: ResearchSourceResultSchema.nullable().optional(),
  news_momentum: ResearchSourceResultSchema.nullable().optional(),
  industry_context: ResearchSourceResultSchema.nullable().optional(),
  culture_values: ResearchSourceResultSchema.nullable().optional(),
  leadership_direction: ResearchSourceResultSchema.nullable().optional(),
  synthesis: z.string().nullable().optional(),
  gaps: z.array(z.string()).default([]),
  completed_at: z.string().nullable().optional(),
});

export type ResearchSourceResult = z.infer<typeof ResearchSourceResultSchema>;
export type ResearchResult = z.infer<typeof ResearchResultSchema>;

export const RESEARCH_CATEGORY_KEYS = [
  'strategic_initiatives',
  'competitive_landscape',
  'news_momentum',
  'industry_context',
  'culture_values',
  'leadership_direction',
] as const;

export function parseResearchData(jsonString: string | null): ResearchResult | null {
  if (!jsonString) return null;
  try {
    const parsed = JSON.parse(jsonString);
    return ResearchResultSchema.parse(parsed);
  } catch (e) {
    console.error('Failed to parse research data:', e);
    return null;
  }
}
