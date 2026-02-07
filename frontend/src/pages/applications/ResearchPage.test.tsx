import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ResearchPage } from './ResearchPage';

beforeEach(() => {
  vi.clearAllMocks();
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/applications/1/research']}>
      <Routes>
        <Route path="/applications/:id/research" element={<ResearchPage />} />
        <Route path="/applications/:id/keywords" element={<div>Keywords Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ResearchPage', () => {
  it('renders placeholder content', () => {
    renderPage();
    expect(screen.getByText('Research phase coming soon.')).toBeInTheDocument();
  });

  it('renders back button', () => {
    renderPage();
    expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument();
  });

  it('renders wizard step indicator at step 3', () => {
    renderPage();
    expect(screen.getByText('Research')).toBeInTheDocument();
  });
});
