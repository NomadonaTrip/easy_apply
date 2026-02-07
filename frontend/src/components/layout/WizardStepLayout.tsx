import type { ReactNode } from 'react';

const STEPS = [
  { label: 'Input', step: 1 },
  { label: 'Keywords', step: 2 },
  { label: 'Research', step: 3 },
  { label: 'Review', step: 4 },
  { label: 'Export', step: 5 },
] as const;

interface WizardStepLayoutProps {
  children: ReactNode;
  currentStep: number;
}

export function WizardStepLayout({ children, currentStep }: WizardStepLayoutProps) {
  return (
    <div className="w-full px-4 md:px-6 mx-auto max-w-full lg:max-w-[800px] xl:max-w-[900px] py-8 lg:py-10">
      {/* Mobile: compact step indicator */}
      <div className="lg:hidden mb-6 flex items-center justify-center gap-2">
        <span className="text-sm font-medium text-primary">
          Step {currentStep} of {STEPS.length}
        </span>
        <div className="flex gap-1">
          {STEPS.map(({ step }) => (
            <div
              key={step}
              className={`h-2 w-2 rounded-full ${
                step < currentStep
                  ? 'bg-primary'
                  : step === currentStep
                    ? 'bg-primary'
                    : 'bg-muted'
              }`}
            />
          ))}
        </div>
      </div>

      {/* Desktop: numbered step circles with connecting lines */}
      <div className="hidden lg:flex items-center mb-8">
        {STEPS.map(({ label, step }, i) => {
          const isComplete = step < currentStep;
          const isCurrent = step === currentStep;
          const isPending = step > currentStep;
          return (
            <div key={step} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center">
                <div
                  className={`h-8 w-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    isComplete
                      ? 'bg-primary text-primary-foreground'
                      : isCurrent
                        ? 'bg-accent border-2 border-primary text-foreground'
                        : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {isComplete ? '\u2713' : step}
                </div>
                <span
                  className={`mt-1 text-xs ${
                    isPending ? 'text-muted-foreground' : 'text-foreground'
                  }`}
                >
                  {label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-2 mt-[-1rem] ${
                    step < currentStep ? 'bg-primary' : 'bg-border'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {children}
    </div>
  );
}
