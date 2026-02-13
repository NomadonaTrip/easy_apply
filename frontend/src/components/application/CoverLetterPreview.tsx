import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import { ToneSelector } from './ToneSelector';
import { useGenerateCoverLetter } from '@/hooks/useGeneration';
import { ConstraintWarnings } from './ConstraintWarnings';
import { RefreshCw, Mail, Edit2, Loader2, AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { CoverLetterTone } from '@/api/applications';

interface CoverLetterPreviewProps {
  applicationId: number;
  coverLetterContent: string | null;
  currentTone: CoverLetterTone | null;
  generationStatus: string;
  violationsFixed?: number;
  warnings?: string[];
}

const TONE_LABELS: Record<string, string> = {
  formal: 'Formal',
  conversational: 'Conversational',
  match_culture: 'Culture-Matched',
};

export function CoverLetterPreview({
  applicationId,
  coverLetterContent,
  currentTone,
  generationStatus,
  violationsFixed,
  warnings,
}: CoverLetterPreviewProps) {
  const [selectedTone, setSelectedTone] = useState<CoverLetterTone>(currentTone || 'formal');
  const [showToneDialog, setShowToneDialog] = useState(false);
  const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false);
  const generateCoverLetter = useGenerateCoverLetter();
  const isGenerating = generateCoverLetter.isPending || generationStatus === 'generating_cover_letter';

  const handleGenerate = () => {
    generateCoverLetter.mutate({
      applicationId,
      tone: selectedTone,
    });
  };

  const handleRegenerateClick = () => {
    if (coverLetterContent) {
      setShowRegenerateConfirm(true);
    } else {
      handleGenerate();
    }
  };

  const confirmRegenerate = () => {
    setShowRegenerateConfirm(false);
    handleGenerate();
  };

  const handleRegenerateWithNewTone = () => {
    setShowToneDialog(false);
    generateCoverLetter.mutate({
      applicationId,
      tone: selectedTone,
    });
  };

  const handleToneDialogChange = (open: boolean) => {
    if (!open) {
      // Reset tone to current when dialog is dismissed
      setSelectedTone(currentTone || 'formal');
    }
    setShowToneDialog(open);
  };

  // Error state
  if (generateCoverLetter.isError) {
    return (
      <Card>
        <CardContent className="p-8">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <div className="ml-2">
              <p className="font-medium">Generation failed</p>
              <p className="text-sm">
                {generateCoverLetter.error instanceof Error
                  ? generateCoverLetter.error.message
                  : 'An unexpected error occurred'}
              </p>
            </div>
          </Alert>
          <div className="mt-4 text-center">
            <Button onClick={handleGenerate} disabled={isGenerating}>
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // No content yet - show tone selector and generate button
  if (!coverLetterContent && !isGenerating) {
    return (
      <Card>
        <CardContent className="p-6 space-y-6">
          <div className="text-center mb-4">
            <Mail className="mx-auto h-12 w-12 text-muted-foreground mb-4" aria-hidden="true" />
            <h3 className="text-lg font-medium mb-2">Generate Cover Letter</h3>
            <p className="text-muted-foreground">
              Select a tone and generate a tailored cover letter.
            </p>
          </div>

          <ToneSelector
            value={selectedTone}
            onChange={setSelectedTone}
            disabled={generateCoverLetter.isPending}
          />

          <Button
            onClick={handleGenerate}
            disabled={generateCoverLetter.isPending}
            className="w-full"
          >
            {generateCoverLetter.isPending ? 'Generating...' : 'Generate Cover Letter'}
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Generating - show loading state
  if (isGenerating && !coverLetterContent) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <Loader2 className="mx-auto h-12 w-12 text-primary animate-spin mb-4" aria-hidden="true" />
          <h3 className="text-lg font-medium mb-2">Generating Cover Letter...</h3>
          <p className="text-muted-foreground">
            Crafting a personalized letter with{' '}
            {TONE_LABELS[selectedTone]?.toLowerCase() || 'selected'} tone.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Content available - show preview
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Mail className="h-5 w-5" aria-hidden="true" />
          Cover Letter Preview
        </CardTitle>
        <div className="flex items-center gap-2">
          {currentTone && (
            <Badge variant="outline" className="text-xs">
              {TONE_LABELS[currentTone] || currentTone}
            </Badge>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowToneDialog(true)}
            disabled={isGenerating}
          >
            <Edit2 className="h-4 w-4 mr-1" aria-hidden="true" />
            Change Tone
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRegenerateClick}
            disabled={isGenerating}
          >
            {isGenerating ? (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" aria-hidden="true" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-1" aria-hidden="true" />
            )}
            Regenerate
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {(generateCoverLetter.data || violationsFixed !== undefined || warnings !== undefined) && (
          <ConstraintWarnings
            violationsFixed={generateCoverLetter.data?.violations_fixed ?? violationsFixed ?? 0}
            warnings={generateCoverLetter.data?.warnings ?? warnings ?? []}
          />
        )}
        <div className="bg-muted/30 p-6 rounded-lg max-h-[600px] overflow-y-auto">
          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
            {coverLetterContent}
          </pre>
        </div>
      </CardContent>

      {/* Tone change dialog */}
      <Dialog open={showToneDialog} onOpenChange={handleToneDialogChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Regenerate with Different Tone</DialogTitle>
            <DialogDescription>
              Select a new tone. This will replace your current cover letter.
            </DialogDescription>
          </DialogHeader>
          <ToneSelector
            value={selectedTone}
            onChange={setSelectedTone}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => handleToneDialogChange(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleRegenerateWithNewTone}
              disabled={generateCoverLetter.isPending}
            >
              {generateCoverLetter.isPending ? 'Generating...' : 'Regenerate'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Regenerate confirmation dialog */}
      <Dialog open={showRegenerateConfirm} onOpenChange={setShowRegenerateConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Regenerate Cover Letter?</DialogTitle>
            <DialogDescription>
              This will replace the current cover letter with a new generation. The existing content will be lost.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRegenerateConfirm(false)}>
              Cancel
            </Button>
            <Button onClick={confirmRegenerate}>
              Regenerate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
