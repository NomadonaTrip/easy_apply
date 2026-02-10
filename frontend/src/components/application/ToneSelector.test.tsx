import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToneSelector } from './ToneSelector';

describe('ToneSelector', () => {
  it('renders three tone options', () => {
    render(<ToneSelector value="formal" onChange={vi.fn()} />);

    expect(screen.getByText('Formal')).toBeInTheDocument();
    expect(screen.getByText('Conversational')).toBeInTheDocument();
    expect(screen.getByText('Match Company Culture')).toBeInTheDocument();
  });

  it('displays descriptions for each tone option', () => {
    render(<ToneSelector value="formal" onChange={vi.fn()} />);

    expect(screen.getByText(/Professional, traditional business letter/)).toBeInTheDocument();
    expect(screen.getByText(/Warm but professional/)).toBeInTheDocument();
    expect(screen.getByText(/Adapts tone based on company research/)).toBeInTheDocument();
  });

  it('shows current selection', () => {
    render(<ToneSelector value="formal" onChange={vi.fn()} />);

    const formalRadio = screen.getByRole('radio', { name: /formal/i });
    expect(formalRadio).toBeChecked();
  });

  it('shows conversational as selected when value is conversational', () => {
    render(<ToneSelector value="conversational" onChange={vi.fn()} />);

    const conversationalRadio = screen.getByRole('radio', { name: /conversational/i });
    expect(conversationalRadio).toBeChecked();
  });

  it('calls onChange when selecting a different tone', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<ToneSelector value="formal" onChange={handleChange} />);

    await user.click(screen.getByRole('radio', { name: /conversational/i }));

    expect(handleChange).toHaveBeenCalledWith('conversational');
  });

  it('disables all options when disabled prop is true', () => {
    render(<ToneSelector value="formal" onChange={vi.fn()} disabled />);

    const radios = screen.getAllByRole('radio');
    radios.forEach((radio) => {
      expect(radio).toBeDisabled();
    });
  });

  it('renders the label "Cover Letter Tone"', () => {
    render(<ToneSelector value="formal" onChange={vi.fn()} />);

    expect(screen.getByText('Cover Letter Tone')).toBeInTheDocument();
  });

  it('uses radio group for accessible selection', () => {
    render(<ToneSelector value="formal" onChange={vi.fn()} />);

    expect(screen.getByRole('radiogroup')).toBeInTheDocument();
    expect(screen.getAllByRole('radio')).toHaveLength(3);
  });
});
