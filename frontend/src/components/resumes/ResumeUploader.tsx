import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useResumes, useUploadResume, useDeleteResume, useExtractAllResumes } from '@/hooks/useResumes';
import { Upload, FileText, Trash2, CheckCircle, AlertCircle, Loader2, Sparkles } from 'lucide-react';

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
};

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

/**
 * Component for uploading and managing resume files.
 * Supports drag-and-drop upload of PDF and DOCX files.
 */
export function ResumeUploader() {
  const { data: resumes, isLoading } = useResumes();
  const uploadResume = useUploadResume();
  const deleteResume = useDeleteResume();
  const extractAll = useExtractAllResumes();
  const [error, setError] = useState<string | null>(null);
  const [extractionResult, setExtractionResult] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setError(null);

      for (const file of acceptedFiles) {
        try {
          await uploadResume.mutateAsync(file);
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Upload failed');
        }
      }
    },
    [uploadResume]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_FILE_SIZE,
    onDropRejected: (rejections) => {
      const rejection = rejections[0];
      if (rejection?.errors[0]?.code === 'file-too-large') {
        setError('File too large. Maximum size: 10MB');
      } else if (rejection?.errors[0]?.code === 'file-invalid-type') {
        setError('Invalid file type. Only PDF and DOCX allowed.');
      } else {
        setError('File rejected');
      }
    },
  });

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleDelete = (resumeId: number) => {
    deleteResume.mutate(resumeId);
  };

  const handleExtractAll = async () => {
    setError(null);
    setExtractionResult(null);
    try {
      const result = await extractAll.mutateAsync();
      setExtractionResult(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Extraction failed');
    }
  };

  // Check if there are any unprocessed resumes
  const hasUnprocessed = resumes?.some((r) => !r.processed);

  return (
    <div className="space-y-4">
      {/* Upload Drop Zone */}
      <Card>
        <CardContent className="p-6">
          <div
            {...getRootProps()}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
              transition-colors
              ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-muted-foreground/50'}
              ${uploadResume.isPending ? 'pointer-events-none opacity-50' : ''}
            `}
          >
            <input {...getInputProps()} aria-label="Upload resume file" />
            {uploadResume.isPending ? (
              <Loader2 className="mx-auto h-10 w-10 text-muted-foreground mb-4 animate-spin" />
            ) : (
              <Upload className="mx-auto h-10 w-10 text-muted-foreground mb-4" />
            )}
            {isDragActive ? (
              <p className="text-primary font-medium">Drop files here...</p>
            ) : uploadResume.isPending ? (
              <p className="text-muted-foreground">Uploading...</p>
            ) : (
              <>
                <p className="text-muted-foreground">
                  Drag & drop resume files, or click to select
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  PDF or DOCX, max 10MB
                </p>
              </>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="flex items-center gap-2 text-destructive mt-4">
              <AlertCircle className="h-4 w-4" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          {/* Extraction Result */}
          {extractionResult && (
            <div className="flex items-center gap-2 text-green-600 bg-green-50 p-3 rounded-md mt-4">
              <CheckCircle className="h-5 w-5" />
              <p>{extractionResult}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Extract All Button */}
      {hasUnprocessed && (
        <Button
          onClick={handleExtractAll}
          disabled={extractAll.isPending}
          className="w-full"
          variant="secondary"
        >
          {extractAll.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Extracting Skills...
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-4 w-4" />
              Extract Skills from All Resumes
            </>
          )}
        </Button>
      )}

      {/* Uploaded Resumes List */}
      {isLoading ? (
        <div className="flex items-center justify-center p-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">Loading resumes...</span>
        </div>
      ) : resumes && resumes.length > 0 ? (
        <Card>
          <CardContent className="p-4">
            <h3 className="font-medium mb-3">Uploaded Resumes</h3>
            <ul className="space-y-2">
              {resumes.map((resume) => (
                <li
                  key={resume.id}
                  className="flex items-center justify-between p-3 bg-muted rounded-md"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{resume.filename}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatFileSize(resume.file_size)} • {resume.file_type.toUpperCase()}
                        {resume.processed && (
                          <span className="ml-2 text-green-600">
                            <CheckCircle className="inline h-3 w-3 mr-1" />
                            Processed
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(resume.id)}
                    disabled={deleteResume.isPending}
                    aria-label={`Delete ${resume.filename}`}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : (
        <p className="text-muted-foreground text-center py-4">
          No resumes uploaded yet. Upload a resume to seed your experience database.
        </p>
      )}
    </div>
  );
}
