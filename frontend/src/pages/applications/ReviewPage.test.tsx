import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ReviewPage } from './ReviewPage';

beforeEach(() => {
  vi.clearAllMocks();
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/applications/1/review']}>
      <Routes>
        <Route path="/applications/:id/review" element={<ReviewPage />} />
        <Route path="/applications/:id/research" element={<div>Research Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ReviewPage', () => {
  it('renders placeholder content', () => {
    renderPage();
    expect(screen.getByText('Review phase coming soon.')).toBeInTheDocument();
  });

  it('renders back button', () => {
    renderPage();
    expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument();
  });

  it('renders wizard step indicator at step 4', () => {
    renderPage();
    expect(screen.getByText('Review')).toBeInTheDocument();
  });
});
