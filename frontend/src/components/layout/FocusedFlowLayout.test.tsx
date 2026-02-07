import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FocusedFlowLayout } from './FocusedFlowLayout';

describe('FocusedFlowLayout', () => {
  it('renders children', () => {
    render(
      <FocusedFlowLayout>
        <div>Test Content</div>
      </FocusedFlowLayout>,
    );
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('renders role pill when roleName is provided', () => {
    render(
      <FocusedFlowLayout roleName="Software Engineer">
        <div>Content</div>
      </FocusedFlowLayout>,
    );
    expect(screen.getByText('Software Engineer')).toBeInTheDocument();
  });

  it('renders progress bar when progressStep is provided', () => {
    const { container } = render(
      <FocusedFlowLayout progressStep={3} totalSteps={5}>
        <div>Content</div>
      </FocusedFlowLayout>,
    );
    // 5 progress segments
    const segments = container.querySelectorAll('.rounded-full.h-1');
    expect(segments.length).toBe(5);
  });

  it('does not render role pill or progress bar when not provided', () => {
    const { container } = render(
      <FocusedFlowLayout>
        <div>Content</div>
      </FocusedFlowLayout>,
    );
    const segments = container.querySelectorAll('.rounded-full.h-1');
    expect(segments.length).toBe(0);
  });
});
