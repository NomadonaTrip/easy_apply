import { apiRequest } from './client';

export interface Application {
  id: number;
  role_id: number;
  company_name: string;
  job_posting: string;
  job_url: string | null;
  status: string;
  keywords: string | null;
  research_data: string | null;
  resume_content: string | null;
  cover_letter_content: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationCreate {
  company_name: string;
  job_posting: string;
  job_url?: string;
}

export interface Keyword {
  text: string;
  priority: number;
  category: string;
}

export interface KeywordExtractionResponse {
  application_id: number;
  keywords: Keyword[];
  status: string;
}

export async function getApplications(): Promise<Application[]> {
  return apiRequest<Application[]>('/applications');
}

export async function getApplication(id: number): Promise<Application> {
  return apiRequest<Application>(`/applications/${id}`);
}

export async function createApplication(data: ApplicationCreate): Promise<Application> {
  return apiRequest<Application>('/applications', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function extractKeywords(id: number): Promise<KeywordExtractionResponse> {
  return apiRequest<KeywordExtractionResponse>(`/applications/${id}/keywords/extract`, {
    method: 'POST',
  });
}
