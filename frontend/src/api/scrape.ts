import { apiRequest } from './client';

export interface ScrapeRequest {
  url: string;
}

export interface ScrapeResponse {
  content: string;
  url: string;
}

export function scrapeJobPosting(data: ScrapeRequest): Promise<ScrapeResponse> {
  return apiRequest<ScrapeResponse>('/scrape/job-posting', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
