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
