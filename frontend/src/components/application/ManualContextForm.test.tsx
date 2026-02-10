import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManualContextForm } from './ManualContextForm';

describe('ManualContextForm', () => {
  const defaultProps = {
    gaps: [] as string[],
    onSave: vi.fn(),
    onCancel: vi.fn(),
  };

  it('renders the text area with label', () => {
    render(<ManualContextForm {...defaultProps} />);
    expect(screen.getByLabelText('Additional Context')).toBeInTheDocument();
  });

  it('renders Save and Cancel buttons', () => {
    render(<ManualContextForm {...defaultProps} />);
    expect(
      screen.getByRole('button', { name: /save context/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /cancel/i }),
    ).toBeInTheDocument();
  });

  it('shows character count', () => {
    render(<ManualContextForm {...defaultProps} />);
    expect(screen.getByText('0 / 5000')).toBeInTheDocument();
  });

  it('updates character count on input', async () => {
    const user = userEvent.setup();
    render(<ManualContextForm {...defaultProps} />);
    const textarea = screen.getByLabelText('Additional Context');
    await user.type(textarea, 'Hello');
    expect(screen.getByText('5 / 5000')).toBeInTheDocument();
  });

  it('shows initial value when provided', () => {
    render(
      <ManualContextForm
        {...defaultProps}
        initialValue="Existing context"
      />,
    );
    expect(screen.getByLabelText('Additional Context')).toHaveValue(
      'Existing context',
    );
  });

  it('calls onSave with trimmed value', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<ManualContextForm {...defaultProps} onSave={onSave} />);

    const textarea = screen.getByLabelText('Additional Context');
    await user.type(textarea, '  Some context  ');
    await user.click(screen.getByRole('button', { name: /save context/i }));

    expect(onSave).toHaveBeenCalledWith('Some context');
  });

  it('calls onCancel when Cancel is clicked', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<ManualContextForm {...defaultProps} onCancel={onCancel} />);

    await user.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('shows gap suggestions when gaps are provided', () => {
    render(
      <ManualContextForm
        {...defaultProps}
        gaps={['strategic_initiatives', 'culture_values']}
      />,
    );
    expect(
      screen.getByText('Suggestions Based on Missing Information'),
    ).toBeInTheDocument();
    expect(screen.getByText(/strategic initiatives/i)).toBeInTheDocument();
    expect(screen.getByText(/culture values/i)).toBeInTheDocument();
  });

  it('does not show suggestions when no gaps', () => {
    render(<ManualContextForm {...defaultProps} gaps={[]} />);
    expect(
      screen.queryByText('Suggestions Based on Missing Information'),
    ).not.toBeInTheDocument();
  });

  it('disables buttons when isLoading', () => {
    render(<ManualContextForm {...defaultProps} isLoading />);
    expect(
      screen.getByRole('button', { name: /saving/i }),
    ).toBeDisabled();
    expect(
      screen.getByRole('button', { name: /cancel/i }),
    ).toBeDisabled();
  });

  it('shows remaining characters warning when below 500', async () => {
    const longText = 'x'.repeat(4600);
    render(
      <ManualContextForm {...defaultProps} initialValue={longText} />,
    );
    expect(screen.getByText('400 characters remaining')).toBeInTheDocument();
  });
});
