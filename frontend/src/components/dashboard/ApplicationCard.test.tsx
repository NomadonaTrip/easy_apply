import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ApplicationCard } from './ApplicationCard';
import { TooltipProvider } from '@/components/ui/tooltip';
import type { Application } from '@/api/applications';

const mockApplication: Application = {
  id: 42,
  role_id: 1,
  company_name: 'TechCorp',
  job_posting: 'Developer role',
  job_url: null,
  status: 'researching',
  keywords: null,
  research_data: null,
  resume_content: null,
  cover_letter_content: null,
  created_at: '2026-02-01T10:00:00Z',
  updated_at: '2026-02-03T12:00:00Z',
};

function renderCard(app: Application = mockApplication) {
  return render(
    <BrowserRouter>
      <TooltipProvider>
        <ApplicationCard application={app} />
      </TooltipProvider>
    </BrowserRouter>
  );
}

describe('ApplicationCard', () => {
  it('displays company name', () => {
    renderCard();
    expect(screen.getByText('TechCorp')).toBeInTheDocument();
  });

  it('displays status badge', () => {
    renderCard();
    expect(screen.getByText('Researching')).toBeInTheDocument();
  });

  it('displays relative date', () => {
    renderCard();
    expect(screen.getByText(/ago/)).toBeInTheDocument();
  });

  it('links to application detail page', () => {
    renderCard();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/applications/42');
  });
});
