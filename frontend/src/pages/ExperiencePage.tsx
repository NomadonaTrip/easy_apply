import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card } from '@/components/ui/card';
import { ResumeUploader } from '@/components/resumes';
import { SkillsList, AccomplishmentsList } from '@/components/experience';
import { useExperienceStats } from '@/hooks/useExperience';
import { useRoleStore } from '@/stores/roleStore';
import { Award, FileText, Upload } from 'lucide-react';

export function ExperiencePage() {
  const currentRole = useRoleStore((s) => s.currentRole);
  const { data: stats } = useExperienceStats();

  if (!currentRole) {
    return (
      <div className="container mx-auto p-6">
        <p className="text-muted-foreground">
          Please select a role to view your experience database.
        </p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Experience Database</h1>
          <p className="text-muted-foreground">
            Role: {currentRole.name}
          </p>
        </div>

        {stats && (
          <div className="flex gap-4">
            <Card className="px-4 py-2">
              <div className="text-sm text-muted-foreground">Skills</div>
              <div className="text-2xl font-bold">{stats.total_skills}</div>
            </Card>
            <Card className="px-4 py-2">
              <div className="text-sm text-muted-foreground">Accomplishments</div>
              <div className="text-2xl font-bold">{stats.total_accomplishments}</div>
            </Card>
          </div>
        )}
      </div>

      <Tabs defaultValue="skills" className="space-y-4">
        <TabsList>
          <TabsTrigger value="skills" className="flex items-center gap-2">
            <Award className="h-4 w-4" />
            Skills
          </TabsTrigger>
          <TabsTrigger value="accomplishments" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Accomplishments
          </TabsTrigger>
          <TabsTrigger value="upload" className="flex items-center gap-2">
            <Upload className="h-4 w-4" />
            Upload Resumes
          </TabsTrigger>
        </TabsList>

        <TabsContent value="skills">
          <SkillsList />
        </TabsContent>

        <TabsContent value="accomplishments">
          <AccomplishmentsList />
        </TabsContent>

        <TabsContent value="upload">
          <ResumeUploader />
        </TabsContent>
      </Tabs>
    </div>
  );
}
