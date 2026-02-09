import { describe, it, expect } from 'vitest';
import { parseResearchData } from './parseResearch';

const validResearch = {
  strategic_initiatives: {
    found: true,
    content: 'Acme Corp is expanding into enterprise market with new SaaS platform',
  },
  competitive_landscape: {
    found: true,
    content: 'Main competitors include BigCo and StartupX. Acme differentiates on price.',
  },
  news_momentum: {
    found: true,
    content: 'Recently raised $50M Series C. Launched new product line in Q3.',
  },
  industry_context: {
    found: false,
    reason: 'Limited public information on industry trends',
  },
  culture_values: {
    found: true,
    content: 'Values: Innovation, Integrity, Collaboration',
  },
  leadership_direction: {
    found: true,
    content: 'CEO focused on international expansion and AI integration',
    partial: true,
    partial_note: 'Only public statements available',
  },
  synthesis: 'Acme Corp needs a senior engineer to scale their enterprise platform.',
  gaps: ['industry_context'],
  completed_at: '2026-02-09T12:00:00Z',
};

describe('parseResearchData', () => {
  it('returns null for null input', () => {
    expect(parseResearchData(null)).toBeNull();
  });

  it('returns null for empty string', () => {
    expect(parseResearchData('')).toBeNull();
  });

  it('returns null for invalid JSON', () => {
    expect(parseResearchData('not json')).toBeNull();
  });

  it('parses valid research data', () => {
    const result = parseResearchData(JSON.stringify(validResearch));
    expect(result).not.toBeNull();
    expect(result!.strategic_initiatives?.found).toBe(true);
    expect(result!.strategic_initiatives?.content).toContain('Acme Corp');
    expect(result!.gaps).toEqual(['industry_context']);
    expect(result!.synthesis).toContain('Acme Corp needs');
  });

  it('handles missing optional fields gracefully', () => {
    const minimal = { gaps: [] };
    const result = parseResearchData(JSON.stringify(minimal));
    expect(result).not.toBeNull();
    expect(result!.gaps).toEqual([]);
    expect(result!.strategic_initiatives).toBeUndefined();
  });

  it('handles partial field in source result', () => {
    const result = parseResearchData(JSON.stringify(validResearch));
    expect(result!.leadership_direction?.partial).toBe(true);
    expect(result!.leadership_direction?.partial_note).toContain('public statements');
  });

  it('defaults gaps to empty array when not provided', () => {
    const noGaps = { strategic_initiatives: { found: true, content: 'test' } };
    const result = parseResearchData(JSON.stringify(noGaps));
    expect(result).not.toBeNull();
    expect(result!.gaps).toEqual([]);
  });

  it('returns null for completely wrong data shape', () => {
    // An array instead of object - zod should reject this
    expect(parseResearchData(JSON.stringify([1, 2, 3]))).toBeNull();
  });
});
