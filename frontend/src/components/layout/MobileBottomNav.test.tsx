import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MobileBottomNav } from './MobileBottomNav';

function renderNav() {
  return render(
    <MemoryRouter>
      <MobileBottomNav />
    </MemoryRouter>,
  );
}

describe('MobileBottomNav', () => {
  it('renders three navigation items', () => {
    renderNav();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('New App')).toBeInTheDocument();
    expect(screen.getByText('Profile')).toBeInTheDocument();
  });

  it('renders as nav element with aria-label', () => {
    renderNav();
    const nav = screen.getByRole('navigation', { name: 'Main navigation' });
    expect(nav).toBeInTheDocument();
  });

  it('links to correct routes', () => {
    renderNav();
    expect(screen.getByText('Dashboard').closest('a')).toHaveAttribute('href', '/dashboard');
    expect(screen.getByText('New App').closest('a')).toHaveAttribute('href', '/applications/new');
    expect(screen.getByText('Profile').closest('a')).toHaveAttribute('href', '/roles');
  });
});
