import { apiRequest } from './client';

export type ApplicationStatus =
  | 'created' | 'keywords' | 'researching' | 'reviewed'
  | 'exported' | 'sent' | 'callback' | 'offer' | 'closed';

export interface Application {
  id: number;
  role_id: number;
  company_name: string;
  job_posting: string;
  job_url: string | null;
  status: ApplicationStatus;
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

export interface KeywordWithId extends Keyword {
  _id: string;
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

export async function saveKeywords(id: number, keywords: Keyword[]): Promise<Application> {
  return apiRequest<Application>(`/applications/${id}/keywords`, {
    method: 'PUT',
    body: JSON.stringify({ keywords }),
  });
}

export async function updateApplicationStatus(id: number, status: ApplicationStatus): Promise<Application> {
  return apiRequest<Application>(`/applications/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

export async function startResearch(id: number): Promise<{ status: string }> {
  return apiRequest<{ status: string }>(`/applications/${id}/research`, {
    method: 'POST',
  });
}
