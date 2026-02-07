import { useParams, useNavigate } from 'react-router-dom';
import { WizardStepLayout } from '@/components/layout/WizardStepLayout';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export function ExportPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  return (
    <WizardStepLayout currentStep={5}>
      <Card className="shadow-md">
        <CardContent className="p-6 text-center">
          <p className="text-muted-foreground">Export phase coming soon.</p>
        </CardContent>
      </Card>
      <div className="mt-8 flex justify-start">
        <Button
          variant="ghost"
          onClick={() => navigate(`/applications/${id}/review`)}
        >
          Back
        </Button>
      </div>
    </WizardStepLayout>
  );
}
