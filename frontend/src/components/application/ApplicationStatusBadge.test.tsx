import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ApplicationStatusBadge } from './ApplicationStatusBadge';
import { TooltipProvider } from '@/components/ui/tooltip';

function renderBadge(status: string, showTooltip = true) {
  return render(
    <TooltipProvider>
      <ApplicationStatusBadge status={status as any} showTooltip={showTooltip} />
    </TooltipProvider>
  );
}

describe('ApplicationStatusBadge', () => {
  it('renders correct label for each status', () => {
    const statuses = [
      { value: 'created', label: 'Created' },
      { value: 'keywords', label: 'Keywords' },
      { value: 'researching', label: 'Researching' },
      { value: 'reviewed', label: 'Reviewed' },
      { value: 'exported', label: 'Exported' },
      { value: 'sent', label: 'Sent' },
      { value: 'callback', label: 'Callback' },
      { value: 'offer', label: 'Offer' },
      { value: 'closed', label: 'Closed' },
    ];

    statuses.forEach(({ value, label }) => {
      const { unmount } = renderBadge(value, false);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    });
  });

  it('applies correct color classes for statuses', () => {
    const { unmount: u1 } = renderBadge('researching', false);
    expect(screen.getByText('Researching')).toHaveClass('bg-yellow-100');
    u1();

    const { unmount: u2 } = renderBadge('created', false);
    expect(screen.getByText('Created')).toHaveClass('bg-gray-100');
    u2();

    const { unmount: u3 } = renderBadge('keywords', false);
    expect(screen.getByText('Keywords')).toHaveClass('bg-blue-100');
    u3();

    const { unmount: u4 } = renderBadge('exported', false);
    expect(screen.getByText('Exported')).toHaveClass('bg-green-100');
    u4();
  });

  it('renders without tooltip when showTooltip is false', () => {
    renderBadge('created', false);
    expect(screen.getByText('Created')).toBeInTheDocument();
  });
});
