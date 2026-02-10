import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatsGrid } from './StatsGrid';
import type { Application } from '@/api/applications';

const baseApp: Application = {
  id: 1,
  role_id: 1,
  company_name: 'Test',
  job_posting: 'Test',
  job_url: null,
  status: 'created',
  keywords: null,
  research_data: null,
  manual_context: null,
  generation_status: 'idle',
  resume_content: null,
  cover_letter_content: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

describe('StatsGrid', () => {
  it('renders stat labels', () => {
    render(<StatsGrid applications={[]} />);
    expect(screen.getByText('Total Sent')).toBeInTheDocument();
    expect(screen.getByText('Callbacks')).toBeInTheDocument();
    expect(screen.getByText('Callback Rate')).toBeInTheDocument();
    expect(screen.getByText('Avg Match')).toBeInTheDocument();
  });

  it('computes total sent correctly', () => {
    const apps: Application[] = [
      { ...baseApp, id: 1, status: 'sent' },
      { ...baseApp, id: 2, status: 'callback' },
      { ...baseApp, id: 3, status: 'created' },
    ];
    render(<StatsGrid applications={apps} />);
    // Total Sent: sent + callback = 2
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('shows dash for callback rate when no sent apps', () => {
    render(<StatsGrid applications={[]} />);
    // Callback Rate and Avg Match both show em dash
    const dashes = screen.getAllByText('\u2014');
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it('computes callback rate', () => {
    const apps: Application[] = [
      { ...baseApp, id: 1, status: 'sent' },
      { ...baseApp, id: 2, status: 'callback' },
      { ...baseApp, id: 3, status: 'sent' },
      { ...baseApp, id: 4, status: 'offer' },
    ];
    render(<StatsGrid applications={apps} />);
    // Total Sent: 4 (sent, callback, sent, offer)
    // Callbacks: 2 (callback, offer)
    // Rate: 50%
    expect(screen.getByText('50%')).toBeInTheDocument();
  });
});
