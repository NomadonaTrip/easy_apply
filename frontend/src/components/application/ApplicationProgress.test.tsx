import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ApplicationProgress } from './ApplicationProgress';

describe('ApplicationProgress', () => {
  it('renders all workflow steps', () => {
    render(<ApplicationProgress currentStatus="created" />);
    expect(screen.getByText('Create')).toBeInTheDocument();
    expect(screen.getByText('Keywords')).toBeInTheDocument();
    expect(screen.getByText('Research')).toBeInTheDocument();
    expect(screen.getByText('Review')).toBeInTheDocument();
    expect(screen.getByText('Export')).toBeInTheDocument();
    expect(screen.getByText('Send')).toBeInTheDocument();
  });

  it('highlights the current step', () => {
    render(<ApplicationProgress currentStatus="researching" />);
    const currentStep = screen.getByText('Research').closest('button');
    expect(currentStep?.querySelector('[aria-current="step"]')).toBeInTheDocument();
  });

  it('shows completed steps with checkmarks', () => {
    render(<ApplicationProgress currentStatus="reviewed" />);
    // Steps before "reviewed" (index 3): created(0), keywords(1), researching(2) should be complete
    const buttons = screen.getAllByRole('button');
    // The first 3 buttons should have SVG checkmarks (Check icon)
    const checkIcons = document.querySelectorAll('[data-testid="check-icon"]');
    expect(checkIcons.length).toBe(3);
  });

  it('calls onStepClick for completed steps', () => {
    const handleClick = vi.fn();
    render(<ApplicationProgress currentStatus="reviewed" onStepClick={handleClick} />);

    // Click on "Keywords" step (completed)
    const keywordsButton = screen.getByText('Keywords').closest('button')!;
    fireEvent.click(keywordsButton);
    expect(handleClick).toHaveBeenCalledWith('keywords');
  });

  it('does not call onStepClick for future steps', () => {
    const handleClick = vi.fn();
    render(<ApplicationProgress currentStatus="created" onStepClick={handleClick} />);

    // Click on "Research" step (future, not clickable)
    const researchButton = screen.getByText('Research').closest('button')!;
    fireEvent.click(researchButton);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('handles final outcome statuses (callback, offer, closed)', () => {
    render(<ApplicationProgress currentStatus="callback" />);
    // All workflow steps should be marked complete
    const checkIcons = document.querySelectorAll('[data-testid="check-icon"]');
    expect(checkIcons.length).toBe(6); // all 6 workflow steps complete
  });
});
