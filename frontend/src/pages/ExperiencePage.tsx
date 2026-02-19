import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card } from '@/components/ui/card';
import { ResumeUploader } from '@/components/resumes';
import { SkillsList, AccomplishmentsList, EnrichmentSuggestions } from '@/components/experience';
import { useExperienceStats, useEnrichmentStats } from '@/hooks/useExperience';
import { useRoleStore } from '@/stores/roleStore';
import { Button } from '@/components/ui/button';
import { Award, FileText, Upload, Lightbulb } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export function ExperiencePage() {
  const currentRole = useRoleStore((s) => s.currentRole);
  const { data: stats } = useExperienceStats();
  const { data: enrichmentStats } = useEnrichmentStats();

  const hasData = stats && (stats.total_skills > 0 || stats.total_accomplishments > 0);

  const [activeTab, setActiveTab] = useState<string | undefined>(undefined);

  // Auto-select suggestions tab when enrichment data first loads with pending items.
  // Only fires when activeTab is still undefined (user has not yet manually switched).
  useEffect(() => {
    if (activeTab === undefined && enrichmentStats) {
      if (enrichmentStats.pending_count > 0) {
        setActiveTab("suggestions");
      } else if (hasData) {
        setActiveTab("skills");
      } else {
        setActiveTab("upload");
      }
    }
  }, [enrichmentStats, hasData, activeTab]);

  // Fallback for initial render before data loads
  const tabValue = activeTab ?? (hasData ? "skills" : "upload");

  if (!currentRole) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex flex-col items-center justify-center text-center py-12">
          <p className="text-muted-foreground mb-4">
            Please select a role to view your experience database.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-fluid-2xl font-bold">Experience Database</h1>
          <p className="text-muted-foreground">
            Role: {currentRole.name}
          </p>
        </div>

        {hasData && stats && (
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

      {!hasData && (
        <div className="flex flex-col items-center justify-center text-center py-12">
          <p className="text-muted-foreground mb-4">
            Upload resumes to build your experience database
          </p>
          <Button onClick={() => document.querySelector<HTMLElement>('[value="upload"]')?.click()}>
            Upload
          </Button>
        </div>
      )}

      <Tabs value={tabValue} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="skills" className="flex items-center gap-2">
            <Award className="h-4 w-4" />
            Skills
          </TabsTrigger>
          <TabsTrigger value="accomplishments" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Accomplishments
          </TabsTrigger>
          <TabsTrigger value="suggestions" className="flex items-center gap-2">
            <Lightbulb className="h-4 w-4" />
            Suggestions
            {enrichmentStats && enrichmentStats.pending_count > 0 && (
              <Badge variant="default" className="ml-1 h-5 min-w-5 px-1.5 text-[10px]">
                {enrichmentStats.pending_count}
              </Badge>
            )}
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

        <TabsContent value="suggestions">
          <EnrichmentSuggestions />
        </TabsContent>

        <TabsContent value="upload">
          <ResumeUploader />
        </TabsContent>
      </Tabs>
    </div>
  );
}
