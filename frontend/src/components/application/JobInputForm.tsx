import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useScrapeJobPosting } from '@/hooks/useScrape';
import { Loader2 } from 'lucide-react';

const formSchema = z.object({
  company_name: z.string().min(1, 'Company name is required').max(255),
  job_posting: z.string().min(10, 'Job description must be at least 10 characters'),
  job_url: z.string().url('Please enter a valid URL').optional().or(z.literal('')),
});

type FormData = z.infer<typeof formSchema>;

interface JobInputFormProps {
  onSubmit: (data: FormData) => void;
  isLoading?: boolean;
}

export function JobInputForm({ onSubmit, isLoading }: JobInputFormProps) {
  const [inputMode, setInputMode] = useState<'paste' | 'url'>('paste');
  const [urlInput, setUrlInput] = useState('');
  const scrapeMutation = useScrapeJobPosting();

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      company_name: '',
      job_posting: '',
      job_url: '',
    },
  });

  const handleFormSubmit = (data: FormData) => {
    onSubmit({
      ...data,
      job_url: data.job_url || undefined,
    });
  };

  const handleFetchUrl = async () => {
    if (!urlInput) return;

    try {
      const result = await scrapeMutation.mutateAsync({ url: urlInput });
      setValue('job_posting', result.content);
      setValue('job_url', result.url);
    } catch {
      // Error handled by mutation state
    }
  };

  const handleSwitchToPaste = () => {
    setInputMode('paste');
    scrapeMutation.reset();
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="company_name">Company Name *</Label>
        <Input
          id="company_name"
          placeholder="e.g., Acme Corp"
          {...register('company_name')}
          aria-invalid={!!errors.company_name}
        />
        {errors.company_name && (
          <p className="text-sm text-destructive">{errors.company_name.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label>Job Description *</Label>
        <Tabs value={inputMode} onValueChange={(v) => setInputMode(v as 'paste' | 'url')}>
          <TabsList>
            <TabsTrigger value="paste">Paste Text</TabsTrigger>
            <TabsTrigger value="url">From URL</TabsTrigger>
          </TabsList>

          <TabsContent value="url" className="space-y-4">
            <div className="flex gap-2">
              <Input
                type="url"
                placeholder="https://company.com/jobs/123"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                aria-label="Job posting URL"
              />
              <Button
                type="button"
                onClick={handleFetchUrl}
                disabled={scrapeMutation.isPending || !urlInput}
                aria-busy={scrapeMutation.isPending}
                className="min-w-[100px]"
              >
                {scrapeMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Fetching...
                  </>
                ) : (
                  'Fetch'
                )}
              </Button>
            </div>

            {scrapeMutation.isError && (
              <div className="p-4 bg-destructive/10 rounded-md" role="alert">
                <p className="text-sm text-destructive">
                  {scrapeMutation.error?.message || 'Failed to fetch URL'}
                </p>
                <Button
                  type="button"
                  variant="link"
                  onClick={handleSwitchToPaste}
                  className="p-0 h-auto"
                >
                  Paste manually instead
                </Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="paste">
            {/* Textarea shown below for both modes */}
          </TabsContent>
        </Tabs>

        <Textarea
          id="job_posting"
          placeholder="Paste the full job description here..."
          className="min-h-[200px]"
          {...register('job_posting')}
          aria-invalid={!!errors.job_posting}
        />
        {errors.job_posting && (
          <p className="text-sm text-destructive">{errors.job_posting.message}</p>
        )}
      </div>

      <input type="hidden" {...register('job_url')} />

      <Button type="submit" disabled={isLoading} className="w-full">
        {isLoading ? 'Creating...' : 'Create Application'}
      </Button>
    </form>
  );
}
