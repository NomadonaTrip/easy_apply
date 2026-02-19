import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useSkills } from '@/hooks/useExperience';
import type { Skill } from '@/api/experience';

interface SkillsByCategory {
  [category: string]: Skill[];
}

export function SkillsList() {
  const { data: skills, isLoading, error } = useSkills();

  if (isLoading) {
    return <div className="animate-pulse h-48 bg-muted rounded-md" />;
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-destructive">Failed to load skills</p>
        </CardContent>
      </Card>
    );
  }

  if (!skills || skills.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-center">
          <p className="text-muted-foreground">
            No skills extracted yet. Upload a resume to get started.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Group skills by category
  const skillsByCategory: SkillsByCategory = skills.reduce((acc, skill) => {
    const category = skill.category || 'Uncategorized';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(skill);
    return acc;
  }, {} as SkillsByCategory);

  // Sort categories alphabetically, but put "Uncategorized" last
  const sortedCategories = Object.keys(skillsByCategory).sort((a, b) => {
    if (a === 'Uncategorized') return 1;
    if (b === 'Uncategorized') return -1;
    return a.localeCompare(b);
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Skills</span>
          <Badge variant="secondary">{skills.length} total</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {sortedCategories.map((category) => (
          <div key={category}>
            <h4 className="font-medium text-sm text-muted-foreground mb-2">
              {category} ({skillsByCategory[category].length})
            </h4>
            <div className="flex flex-wrap gap-2">
              {skillsByCategory[category].map((skill) => (
                <div key={skill.id} className="inline-flex items-center gap-1">
                  <Badge variant="outline">
                    {skill.name}
                  </Badge>
                  {skill.source === 'resume' && (
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                      Resume
                    </Badge>
                  )}
                  {skill.source === 'application-enriched' && (
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 bg-primary/10 text-primary">
                      Enriched
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
