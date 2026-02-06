import { useMutation } from '@tanstack/react-query';
import { scrapeJobPosting } from '@/api/scrape';
import type { ScrapeRequest } from '@/api/scrape';

export function useScrapeJobPosting() {
  return useMutation({
    mutationFn: (data: ScrapeRequest) => scrapeJobPosting(data),
  });
}
