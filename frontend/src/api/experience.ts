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
