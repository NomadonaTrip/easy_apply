import { ResumeUploader } from '@/components/resumes';

/**
 * Experience Database Page
 *
 * Allows users to upload resumes and manage their experience data.
 * Skills and accomplishments sections will be added in Story 2.7.
 */
export function ExperiencePage() {
  return (
    <div className="container mx-auto p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Experience Database</h1>
        <p className="text-muted-foreground mt-1">
          Upload your resumes to seed your experience database. The system will extract
          skills and accomplishments for use in tailored applications.
        </p>
      </div>

      <section>
        <h2 className="text-xl font-semibold mb-4">Upload Resumes</h2>
        <ResumeUploader />
      </section>

      {/* Skills and Accomplishments UI will be added in Story 2.6 (Skill Extraction) and Story 2.7 (View Experience Database) */}
    </div>
  );
}
