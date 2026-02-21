import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { formatDistanceToNow } from 'date-fns';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { RefreshCw, FileText, Clock, AlertCircle, Loader2, Check } from 'lucide-react';

interface ResumePreviewProps {
  resumeContent: string | null;
  // Generation mode (optional — omit for review mode)
  generationStatus?: string;
  onGenerate?: () => void;
  isGenerating?: boolean;
  error?: Error | null;
  generatedAt?: string | null;
  // Review mode (optional — omit for generation mode)
  resumeApproved?: boolean;
}

export function ResumePreview({
  resumeContent,
  generationStatus,
  onGenerate,
  isGenerating = false,
  error = null,
  generatedAt = null,
  resumeApproved = false,
}: ResumePreviewProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const isReviewMode = !onGenerate;
  const isGeneratingResume = isGenerating || generationStatus === 'generating_resume';

  const handleRegenerate = () => {
    if (!onGenerate) return;
    if (resumeContent) {
      setShowConfirm(true);
    } else {
      onGenerate();
    }
  };

  const confirmRegenerate = () => {
    if (!onGenerate) return;
    setShowConfirm(false);
    onGenerate();
  };

  // Error state (generation mode only)
  if (!isReviewMode && error) {
    return (
      <Card>
        <CardContent className="p-8">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <div className="ml-2">
              <p className="font-medium">Generation failed</p>
              <p className="text-sm">{error.message}</p>
            </div>
          </Alert>
          <div className="mt-4 text-center">
            <Button onClick={onGenerate} disabled={isGeneratingResume}>
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // No content yet
  if (!resumeContent && !isGeneratingResume) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <FileText className="mx-auto h-12 w-12 text-muted-foreground mb-4" aria-hidden="true" />
          {isReviewMode ? (
            <>
              <h3 className="text-lg font-medium mb-2">Resume Not Yet Generated</h3>
              <p className="text-muted-foreground">
                The resume has not been generated for this application yet.
              </p>
            </>
          ) : (
            <>
              <h3 className="text-lg font-medium mb-2">No Resume Generated</h3>
              <p className="text-muted-foreground mb-4">
                Generate a tailored resume based on your experience and the job requirements.
              </p>
              <Button onClick={onGenerate} disabled={isGeneratingResume}>
                Generate Resume
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    );
  }

  // Generating - show loading state (generation mode only)
  if (!isReviewMode && isGeneratingResume && !resumeContent) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <Loader2 className="mx-auto h-12 w-12 text-primary animate-spin mb-4" aria-hidden="true" />
          <h3 className="text-lg font-medium mb-2">Generating Resume...</h3>
          <p className="text-muted-foreground">
            Analyzing your experience and tailoring content to the job requirements.
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
          <FileText className="h-5 w-5" aria-hidden="true" />
          Resume Preview
        </CardTitle>
        <div className="flex items-center gap-2">
          {isReviewMode ? (
            resumeApproved && (
              <Badge variant="outline" className="text-xs border-success text-success">
                <Check className="h-3 w-3 mr-1" aria-hidden="true" />
                Approved
              </Badge>
            )
          ) : (
            <>
              <Badge variant="outline" className="text-xs">
                <Clock className="h-3 w-3 mr-1" aria-hidden="true" />
                {generatedAt ? (
                  <span title={generatedAt}>
                    Generated {formatDistanceToNow(new Date(generatedAt))} ago
                  </span>
                ) : (
                  'Generated'
                )}
              </Badge>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRegenerate}
                disabled={isGeneratingResume}
              >
                {isGeneratingResume ? (
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" aria-hidden="true" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-1" aria-hidden="true" />
                )}
                Regenerate
              </Button>
            </>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="prose prose-sm max-w-none dark:prose-invert bg-muted/30 p-6 rounded-lg max-h-[600px] overflow-y-auto">
          <ReactMarkdown>{resumeContent ?? ''}</ReactMarkdown>
        </div>
      </CardContent>

      {!isReviewMode && (
        <Dialog open={showConfirm} onOpenChange={setShowConfirm}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Regenerate Resume?</DialogTitle>
              <DialogDescription>
                This will replace the current resume with a new generation. The existing content will be lost.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowConfirm(false)}>
                Cancel
              </Button>
              <Button onClick={confirmRegenerate}>
                Regenerate
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </Card>
  );
}
