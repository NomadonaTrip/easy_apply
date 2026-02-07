import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Sidebar } from './Sidebar';
import * as rolesApi from '@/api/roles';

vi.mock('@/api/roles', () => ({
  getRoles: vi.fn(),
  createRole: vi.fn(),
  deleteRole: vi.fn(),
}));

vi.mock('@/lib/queryClient', () => ({
  queryClient: {
    invalidateQueries: vi.fn(),
    clear: vi.fn(),
  },
}));

function renderSidebar() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(rolesApi.getRoles).mockResolvedValue([]);
  });

  it('renders navigation items', () => {
    renderSidebar();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('New Application')).toBeInTheDocument();
    expect(screen.getByText('Experience DB')).toBeInTheDocument();
    expect(screen.getByText('Manage Roles')).toBeInTheDocument();
  });

  it('renders as aside element with accessible nav', () => {
    renderSidebar();
    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument();
  });

  it('renders nav links with correct hrefs', () => {
    renderSidebar();
    expect(screen.getByText('Dashboard').closest('a')).toHaveAttribute('href', '/dashboard');
    expect(screen.getByText('New Application').closest('a')).toHaveAttribute('href', '/applications/new');
    expect(screen.getByText('Experience DB').closest('a')).toHaveAttribute('href', '/experience');
    expect(screen.getByText('Manage Roles').closest('a')).toHaveAttribute('href', '/roles');
  });
});
