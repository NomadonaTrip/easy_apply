import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ApplicationTable } from './ApplicationTable';
import type { Application } from '@/api/applications';

const mockApps: Application[] = [
  {
    id: 1,
    role_id: 1,
    company_name: 'Acme Corp',
    job_posting: 'Dev role',
    job_url: null,
    status: 'sent',
    keywords: null,
    research_data: null,
    manual_context: null,
    generation_status: 'idle',
    resume_content: null,
    cover_letter_content: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-15T00:00:00Z',
  },
  {
    id: 2,
    role_id: 1,
    company_name: 'TechFlow',
    job_posting: 'Engineer',
    job_url: null,
    status: 'callback',
    keywords: null,
    research_data: null,
    manual_context: null,
    generation_status: 'idle',
    resume_content: null,
    cover_letter_content: null,
    created_at: '2026-01-10T00:00:00Z',
    updated_at: '2026-01-20T00:00:00Z',
  },
];

function renderTable(apps = mockApps) {
  return render(
    <BrowserRouter>
      <TooltipProvider>
        <ApplicationTable applications={apps} />
      </TooltipProvider>
    </BrowserRouter>,
  );
}

describe('ApplicationTable', () => {
  it('renders company names', () => {
    const { container } = renderTable();
    expect(container.textContent).toContain('Acme Corp');
    expect(container.textContent).toContain('TechFlow');
  });

  it('renders column headers in desktop table', () => {
    renderTable();
    expect(screen.getByText('Company')).toBeInTheDocument();
    expect(screen.getByText('Match')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText(/^Date/)).toBeInTheDocument();
    expect(screen.getByText('Action')).toBeInTheDocument();
  });

  it('renders view links', () => {
    renderTable();
    const viewLinks = screen.getAllByText('View');
    expect(viewLinks.length).toBe(2);
  });

  it('renders empty state when no applications', () => {
    const { container } = renderTable([]);
    expect(container.querySelector('table')).toBeInTheDocument();
    expect(container.querySelector('tbody')?.children.length).toBe(0);
  });
});
