import { apiRequest } from './client';

export interface Skill {
  id: number;
  role_id: number;
  name: string;
  category: string | null;
  source: string | null;
  created_at: string;
}

export interface Accomplishment {
  id: number;
  role_id: number;
  description: string;
  context: string | null;
  source: string | null;
  created_at: string;
}

export interface ExperienceData {
  skills: Skill[];
  accomplishments: Accomplishment[];
  skills_count: number;
  accomplishments_count: number;
}

export interface ExperienceStats {
  total_skills: number;
  total_accomplishments: number;
  skills_by_category: Record<string, number>;
}

export async function getExperience(): Promise<ExperienceData> {
  return apiRequest<ExperienceData>('/experience');
}

export async function getSkills(): Promise<Skill[]> {
  return apiRequest<Skill[]>('/experience/skills');
}

export async function getAccomplishments(): Promise<Accomplishment[]> {
  return apiRequest<Accomplishment[]>('/experience/accomplishments');
}

export async function getExperienceStats(): Promise<ExperienceStats> {
  return apiRequest<ExperienceStats>('/experience/stats');
}

// Enrichment types and API functions

export interface EnrichmentCandidate {
  id: number;
  role_id: number;
  application_id: number;
  document_type: string;
  candidate_type: string;
  name: string;
  category: string | null;
  context: string | null;
  status: string;
  created_at: string;
  resolved_at: string | null;
}

export interface EnrichmentCandidateGroup {
  company_name: string;
  candidates: EnrichmentCandidate[];
}

export interface EnrichmentCandidatesResponse {
  candidates: Record<string, EnrichmentCandidateGroup>;
  total_pending: number;
}

export interface EnrichmentStatsResponse {
  pending_count: number;
}

export async function getEnrichmentCandidates(): Promise<EnrichmentCandidatesResponse> {
  return apiRequest<EnrichmentCandidatesResponse>('/experience/enrichment');
}

export async function getEnrichmentStats(): Promise<EnrichmentStatsResponse> {
  return apiRequest<EnrichmentStatsResponse>('/experience/enrichment/stats');
}

export async function acceptCandidate(id: number): Promise<{ status: string; candidate_id: number }> {
  return apiRequest(`/experience/enrichment/${id}/accept`, { method: 'POST' });
}

export async function dismissCandidate(id: number): Promise<{ status: string; candidate_id: number }> {
  return apiRequest(`/experience/enrichment/${id}/dismiss`, { method: 'POST' });
}

export async function bulkResolve(
  ids: number[],
  action: 'accept' | 'dismiss'
): Promise<{ resolved: number; skipped: number }> {
  return apiRequest('/experience/enrichment/bulk', {
    method: 'POST',
    body: JSON.stringify({ candidate_ids: ids, action }),
  });
}

export async function triggerEnrichment(applicationId: number): Promise<{
  application_id: number;
  resume_result: Record<string, unknown> | null;
  cover_letter_result: Record<string, unknown> | null;
  message: string;
}> {
  return apiRequest(`/applications/${applicationId}/enrich`, { method: 'POST' });
}
