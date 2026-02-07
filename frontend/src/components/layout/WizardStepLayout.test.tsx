import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WizardStepLayout } from './WizardStepLayout';

describe('WizardStepLayout', () => {
  it('renders children', () => {
    render(
      <WizardStepLayout currentStep={1}>
        <div>Wizard Content</div>
      </WizardStepLayout>,
    );
    expect(screen.getByText('Wizard Content')).toBeInTheDocument();
  });

  it('renders step labels on desktop view', () => {
    render(
      <WizardStepLayout currentStep={2}>
        <div>Content</div>
      </WizardStepLayout>,
    );
    expect(screen.getByText('Input')).toBeInTheDocument();
    expect(screen.getByText('Keywords')).toBeInTheDocument();
    expect(screen.getByText('Research')).toBeInTheDocument();
    expect(screen.getByText('Review')).toBeInTheDocument();
    expect(screen.getByText('Export')).toBeInTheDocument();
  });

  it('renders mobile step indicator', () => {
    render(
      <WizardStepLayout currentStep={3}>
        <div>Content</div>
      </WizardStepLayout>,
    );
    expect(screen.getByText('Step 3 of 5')).toBeInTheDocument();
  });

  it('shows checkmark for completed steps', () => {
    const { container } = render(
      <WizardStepLayout currentStep={3}>
        <div>Content</div>
      </WizardStepLayout>,
    );
    // Steps 1 and 2 should have checkmarks (\u2713)
    const stepCircles = container.querySelectorAll('.bg-primary.text-primary-foreground');
    expect(stepCircles.length).toBeGreaterThanOrEqual(2);
  });
});
