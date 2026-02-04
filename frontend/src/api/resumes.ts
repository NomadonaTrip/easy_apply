/**
 * API client for resume upload operations.
 *
 * Uses centralized apiRequest for GET/DELETE operations.
 * Upload uses custom fetch due to multipart/form-data requirement.
 */

import { apiRequest } from './client';
import { useRoleStore } from '@/stores/roleStore';

const API_BASE = '/api/v1';

export interface Resume {
  id: number;
  role_id: number;
  filename: string;
  file_type: string;
  file_size: number;
  file_path: string;
  uploaded_at: string;
  processed: boolean;
}

export interface ExtractionResult {
  message: string;
  skills_count: number;
  accomplishments_count: number;
}

export interface BulkExtractionResult {
  message: string;
  resumes_processed: number;
  total_skills: number;
  total_accomplishments: number;
}

/**
 * Upload a resume file.
 * Uses custom fetch with multipart/form-data (apiRequest doesn't support FormData).
 */
export async function uploadResume(file: File): Promise<Resume> {
  const { currentRole } = useRoleStore.getState();

  if (!currentRole) {
    throw new Error('No role selected. Please select a role first.');
  }

  const formData = new FormData();
  formData.append('file', file);

  // Note: Don't set Content-Type header - browser will set it with boundary for multipart
  const response = await fetch(`${API_BASE}/resumes/upload`, {
    method: 'POST',
    body: formData,
    credentials: 'include',
    headers: {
      'X-Role-Id': currentRole.id.toString(),
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json();
}

/**
 * Get all resumes for the current role.
 * Uses centralized apiRequest which handles X-Role-Id header injection.
 */
export async function getResumes(): Promise<Resume[]> {
  return apiRequest<Resume[]>('/resumes');
}

/**
 * Delete a resume by ID.
 * Uses centralized apiRequest which handles X-Role-Id header injection.
 */
export async function deleteResume(resumeId: number): Promise<void> {
  return apiRequest<void>(`/resumes/${resumeId}`, { method: 'DELETE' });
}

/**
 * Extract skills and accomplishments from a single resume.
 */
export async function extractFromResume(resumeId: number): Promise<ExtractionResult> {
  return apiRequest<ExtractionResult>(`/resumes/${resumeId}/extract`, {
    method: 'POST',
  });
}

/**
 * Extract skills and accomplishments from all unprocessed resumes.
 */
export async function extractAllResumes(): Promise<BulkExtractionResult> {
  return apiRequest<BulkExtractionResult>('/resumes/extract-all', {
    method: 'POST',
  });
}
