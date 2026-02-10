import { apiRequest } from './client';
import type { CoverLetterTone } from './applications';

export interface GenerateResumeResponse {
  message: string;
  resume_content: string;
  status: string;
}

export interface GenerateCoverLetterResponse {
  message: string;
  cover_letter_content: string;
  status: string;
}

export interface GenerationStatusResponse {
  generation_status: string;
  has_resume: boolean;
  has_cover_letter: boolean;
}

export async function generateResume(applicationId: number): Promise<GenerateResumeResponse> {
  return apiRequest<GenerateResumeResponse>(
    `/applications/${applicationId}/generate/resume`,
    { method: 'POST' },
  );
}

export async function generateCoverLetter(
  applicationId: number,
  tone: CoverLetterTone = 'formal',
): Promise<GenerateCoverLetterResponse> {
  return apiRequest<GenerateCoverLetterResponse>(
    `/applications/${applicationId}/generate/cover-letter`,
    {
      method: 'POST',
      body: JSON.stringify({ tone }),
    },
  );
}

export async function getGenerationStatus(applicationId: number): Promise<GenerationStatusResponse> {
  return apiRequest<GenerationStatusResponse>(
    `/applications/${applicationId}/generation/status`,
  );
}
