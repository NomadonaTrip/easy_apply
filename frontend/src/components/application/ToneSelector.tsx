import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Card, CardContent } from '@/components/ui/card';
import type { CoverLetterTone } from '@/api/applications';

interface ToneSelectorProps {
  value: CoverLetterTone;
  onChange: (tone: CoverLetterTone) => void;
  disabled?: boolean;
}

const TONE_OPTIONS = [
  {
    value: 'formal',
    label: 'Formal',
    description: 'Professional, traditional business letter style. Best for conservative industries.',
  },
  {
    value: 'conversational',
    label: 'Conversational',
    description: 'Warm but professional, more personal touch. Good for startups and creative roles.',
  },
  {
    value: 'match_culture',
    label: 'Match Company Culture',
    description: 'Adapts tone based on company research. Recommended when research is complete.',
  },
];

export function ToneSelector({ value, onChange, disabled }: ToneSelectorProps) {
  return (
    <div className="space-y-3">
      <Label className="text-base font-medium">Cover Letter Tone</Label>
      <RadioGroup
        value={value}
        onValueChange={(v) => onChange(v as CoverLetterTone)}
        disabled={disabled}
        className="space-y-3"
      >
        {TONE_OPTIONS.map((option) => (
          <Card
            key={option.value}
            className={`transition-colors ${
              value === option.value ? 'border-primary' : ''
            } ${disabled ? 'opacity-50' : ''}`}
          >
            <CardContent className="p-4 flex items-start gap-3">
              <RadioGroupItem value={option.value} id={option.value} />
              <div className="flex-1">
                <Label
                  htmlFor={option.value}
                  className="font-medium cursor-pointer"
                >
                  {option.label}
                </Label>
                <p className="text-sm text-muted-foreground mt-1">
                  {option.description}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </RadioGroup>
    </div>
  );
}
