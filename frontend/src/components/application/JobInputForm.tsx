import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

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
  const {
    register,
    handleSubmit,
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
        <Label htmlFor="job_posting">Job Description *</Label>
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

      <div className="space-y-2">
        <Label htmlFor="job_url">Job URL (optional)</Label>
        <Input
          id="job_url"
          type="url"
          placeholder="https://company.com/jobs/123"
          {...register('job_url')}
          aria-invalid={!!errors.job_url}
        />
        {errors.job_url && (
          <p className="text-sm text-destructive">{errors.job_url.message}</p>
        )}
      </div>

      <Button type="submit" disabled={isLoading} className="w-full">
        {isLoading ? 'Creating...' : 'Create Application'}
      </Button>
    </form>
  );
}
