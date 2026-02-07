import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ExportPage } from './ExportPage';

beforeEach(() => {
  vi.clearAllMocks();
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/applications/1/export']}>
      <Routes>
        <Route path="/applications/:id/export" element={<ExportPage />} />
        <Route path="/applications/:id/review" element={<div>Review Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ExportPage', () => {
  it('renders placeholder content', () => {
    renderPage();
    expect(screen.getByText('Export phase coming soon.')).toBeInTheDocument();
  });

  it('renders back button', () => {
    renderPage();
    expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument();
  });

  it('renders wizard step indicator at step 5', () => {
    renderPage();
    expect(screen.getByText('Export')).toBeInTheDocument();
  });
});
