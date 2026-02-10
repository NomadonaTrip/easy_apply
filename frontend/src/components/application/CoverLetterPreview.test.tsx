import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { CoverLetterPreview } from './CoverLetterPreview';
import * as generationApi from '@/api/generation';
import { useRoleStore } from '@/stores/roleStore';

vi.mock('@/api/generation', () => ({
  generateCoverLetter: vi.fn(),
  generateResume: vi.fn(),
  getGenerationStatus: vi.fn(),
}));

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
}

function renderPreview(props: Partial<React.ComponentProps<typeof CoverLetterPreview>> = {}) {
  useRoleStore.setState({
    currentRole: { id: 1, user_id: 1, name: 'Dev', created_at: '2026-01-01' },
  });

  const queryClient = createTestQueryClient();
  const defaultProps = {
    applicationId: 1,
    coverLetterContent: null as string | null,
    currentTone: null as React.ComponentProps<typeof CoverLetterPreview>['currentTone'],
    generationStatus: 'idle',
    ...props,
  };

  return render(
    <QueryClientProvider client={queryClient}>
      <CoverLetterPreview {...defaultProps} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('CoverLetterPreview', () => {
  describe('empty state', () => {
    it('shows generate button when no content exists', () => {
      renderPreview();

      expect(screen.getByRole('button', { name: /generate cover letter/i })).toBeInTheDocument();
    });

    it('shows tone selector when no content exists', () => {
      renderPreview();

      expect(screen.getByText('Cover Letter Tone')).toBeInTheDocument();
      expect(screen.getByText('Formal')).toBeInTheDocument();
      expect(screen.getByText('Conversational')).toBeInTheDocument();
      expect(screen.getByText('Match Company Culture')).toBeInTheDocument();
    });

    it('defaults to formal tone', () => {
      renderPreview();

      const formalRadio = screen.getByRole('radio', { name: /formal/i });
      expect(formalRadio).toBeChecked();
    });

    it('shows empty state message', () => {
      renderPreview();

      expect(screen.getByRole('heading', { name: 'Generate Cover Letter' })).toBeInTheDocument();
      expect(screen.getByText(/Select a tone and generate/)).toBeInTheDocument();
    });
  });

  describe('tone selection', () => {
    it('allows selecting a different tone', async () => {
      const user = userEvent.setup();
      renderPreview();

      await user.click(screen.getByRole('radio', { name: /conversational/i }));

      expect(screen.getByRole('radio', { name: /conversational/i })).toBeChecked();
    });
  });

  describe('generation trigger', () => {
    it('calls generateCoverLetter API with selected tone on button click', async () => {
      const user = userEvent.setup();
      vi.mocked(generationApi.generateCoverLetter).mockResolvedValue({
        message: 'Cover letter generated',
        cover_letter_content: 'Dear Hiring Manager,\n\nTest content.',
        status: 'complete',
      });
      renderPreview();

      await user.click(screen.getByRole('button', { name: /generate cover letter/i }));

      await waitFor(() => {
        expect(generationApi.generateCoverLetter).toHaveBeenCalledWith(1, 'formal');
      });
    });

    it('passes non-default tone to API', async () => {
      const user = userEvent.setup();
      vi.mocked(generationApi.generateCoverLetter).mockResolvedValue({
        message: 'Cover letter generated',
        cover_letter_content: 'Hey there!\n\nTest content.',
        status: 'complete',
      });
      renderPreview();

      await user.click(screen.getByRole('radio', { name: /conversational/i }));
      await user.click(screen.getByRole('button', { name: /generate cover letter/i }));

      await waitFor(() => {
        expect(generationApi.generateCoverLetter).toHaveBeenCalledWith(1, 'conversational');
      });
    });
  });

  describe('loading state', () => {
    it('shows generating message during generation', () => {
      renderPreview({ generationStatus: 'generating_cover_letter' });

      expect(screen.getByText('Generating Cover Letter...')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('shows error message when generation fails', async () => {
      const user = userEvent.setup();
      vi.mocked(generationApi.generateCoverLetter).mockRejectedValue(
        new Error('LLM service unavailable'),
      );
      renderPreview();

      await user.click(screen.getByRole('button', { name: /generate cover letter/i }));

      await waitFor(() => {
        expect(screen.getByText('Generation failed')).toBeInTheDocument();
        expect(screen.getByText('LLM service unavailable')).toBeInTheDocument();
      });
    });

    it('shows Try Again button after error', async () => {
      const user = userEvent.setup();
      vi.mocked(generationApi.generateCoverLetter).mockRejectedValue(
        new Error('Service error'),
      );
      renderPreview();

      await user.click(screen.getByRole('button', { name: /generate cover letter/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
      });
    });

    it('retries generation when Try Again is clicked', async () => {
      const user = userEvent.setup();
      vi.mocked(generationApi.generateCoverLetter)
        .mockRejectedValueOnce(new Error('Service error'))
        .mockResolvedValueOnce({
          message: 'Cover letter generated',
          cover_letter_content: 'Dear Hiring Manager,\n\nRetried content.',
          status: 'complete',
        });
      renderPreview();

      await user.click(screen.getByRole('button', { name: /generate cover letter/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /try again/i }));

      await waitFor(() => {
        expect(generationApi.generateCoverLetter).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('content preview', () => {
    it('displays cover letter content as plain text', () => {
      renderPreview({
        coverLetterContent: 'Dear Hiring Manager,\n\nI am writing to express my interest.',
        currentTone: 'formal',
        generationStatus: 'complete',
      });

      expect(screen.getByText(/Dear Hiring Manager/)).toBeInTheDocument();
      expect(screen.getByText(/I am writing to express my interest/)).toBeInTheDocument();
    });

    it('shows tone badge when content exists', () => {
      renderPreview({
        coverLetterContent: 'Some content',
        currentTone: 'formal',
        generationStatus: 'complete',
      });

      expect(screen.getByText('Formal')).toBeInTheDocument();
    });

    it('shows culture-matched badge for match_culture tone', () => {
      renderPreview({
        coverLetterContent: 'Some content',
        currentTone: 'match_culture',
        generationStatus: 'complete',
      });

      expect(screen.getByText('Culture-Matched')).toBeInTheDocument();
    });

    it('shows "Cover Letter Preview" title', () => {
      renderPreview({
        coverLetterContent: 'Some content',
        currentTone: 'formal',
        generationStatus: 'complete',
      });

      expect(screen.getByText('Cover Letter Preview')).toBeInTheDocument();
    });
  });

  describe('regeneration with tone change', () => {
    it('shows Change Tone button when content exists', () => {
      renderPreview({
        coverLetterContent: 'Some content',
        currentTone: 'formal',
        generationStatus: 'complete',
      });

      expect(screen.getByRole('button', { name: /change tone/i })).toBeInTheDocument();
    });

    it('shows Regenerate button when content exists', () => {
      renderPreview({
        coverLetterContent: 'Some content',
        currentTone: 'formal',
        generationStatus: 'complete',
      });

      expect(screen.getByRole('button', { name: /regenerate/i })).toBeInTheDocument();
    });

    it('opens tone change dialog when Change Tone is clicked', async () => {
      const user = userEvent.setup();
      renderPreview({
        coverLetterContent: 'Some content',
        currentTone: 'formal',
        generationStatus: 'complete',
      });

      await user.click(screen.getByRole('button', { name: /change tone/i }));

      await waitFor(() => {
        expect(screen.getByText('Regenerate with Different Tone')).toBeInTheDocument();
        expect(screen.getByText(/This will replace your current cover letter/)).toBeInTheDocument();
      });
    });

    it('regenerates with new tone from dialog', async () => {
      const user = userEvent.setup();
      vi.mocked(generationApi.generateCoverLetter).mockResolvedValue({
        message: 'Cover letter generated',
        cover_letter_content: 'New content',
        status: 'complete',
      });
      renderPreview({
        coverLetterContent: 'Old content',
        currentTone: 'formal',
        generationStatus: 'complete',
      });

      await user.click(screen.getByRole('button', { name: /change tone/i }));

      await waitFor(() => {
        expect(screen.getByText('Regenerate with Different Tone')).toBeInTheDocument();
      });

      // Select conversational tone in dialog
      const dialogRadios = screen.getAllByRole('radio', { name: /conversational/i });
      await user.click(dialogRadios[dialogRadios.length - 1]);

      // Click Regenerate in dialog
      const dialogButtons = screen.getAllByRole('button', { name: /regenerate/i });
      const confirmButton = dialogButtons[dialogButtons.length - 1];
      await user.click(confirmButton);

      await waitFor(() => {
        expect(generationApi.generateCoverLetter).toHaveBeenCalledWith(1, 'conversational');
      });
    });

    it('closes dialog on cancel and resets tone', async () => {
      const user = userEvent.setup();
      renderPreview({
        coverLetterContent: 'Some content',
        currentTone: 'formal',
        generationStatus: 'complete',
      });

      await user.click(screen.getByRole('button', { name: /change tone/i }));

      await waitFor(() => {
        expect(screen.getByText('Regenerate with Different Tone')).toBeInTheDocument();
      });

      // Select a different tone before canceling
      const dialogRadios = screen.getAllByRole('radio', { name: /conversational/i });
      await user.click(dialogRadios[dialogRadios.length - 1]);

      await user.click(screen.getByRole('button', { name: /cancel/i }));

      await waitFor(() => {
        expect(screen.queryByText('Regenerate with Different Tone')).not.toBeInTheDocument();
      });
    });
  });

  describe('direct regeneration', () => {
    it('shows confirmation dialog when Regenerate clicked with existing content', async () => {
      const user = userEvent.setup();
      renderPreview({
        coverLetterContent: 'Existing content',
        currentTone: 'formal',
        generationStatus: 'complete',
      });

      await user.click(screen.getByRole('button', { name: /regenerate/i }));

      await waitFor(() => {
        expect(screen.getByText('Regenerate Cover Letter?')).toBeInTheDocument();
        expect(screen.getByText(/This will replace the current cover letter/)).toBeInTheDocument();
      });
    });

    it('regenerates after confirming in dialog', async () => {
      const user = userEvent.setup();
      vi.mocked(generationApi.generateCoverLetter).mockResolvedValue({
        message: 'Cover letter generated',
        cover_letter_content: 'Regenerated content',
        status: 'complete',
      });
      renderPreview({
        coverLetterContent: 'Existing content',
        currentTone: 'formal',
        generationStatus: 'complete',
      });

      await user.click(screen.getByRole('button', { name: /regenerate/i }));

      await waitFor(() => {
        expect(screen.getByText('Regenerate Cover Letter?')).toBeInTheDocument();
      });

      // Click the confirm Regenerate button in the confirmation dialog
      const dialogButtons = screen.getAllByRole('button', { name: /regenerate/i });
      const confirmButton = dialogButtons[dialogButtons.length - 1];
      await user.click(confirmButton);

      await waitFor(() => {
        expect(generationApi.generateCoverLetter).toHaveBeenCalledWith(1, 'formal');
      });
    });

    it('does not regenerate when confirmation canceled', async () => {
      const user = userEvent.setup();
      renderPreview({
        coverLetterContent: 'Existing content',
        currentTone: 'formal',
        generationStatus: 'complete',
      });

      await user.click(screen.getByRole('button', { name: /regenerate/i }));

      await waitFor(() => {
        expect(screen.getByText('Regenerate Cover Letter?')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /cancel/i }));

      await waitFor(() => {
        expect(screen.queryByText('Regenerate Cover Letter?')).not.toBeInTheDocument();
      });

      expect(generationApi.generateCoverLetter).not.toHaveBeenCalled();
    });
  });
});
