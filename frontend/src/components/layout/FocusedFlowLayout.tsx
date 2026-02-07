import type { ReactNode } from 'react';

interface FocusedFlowLayoutProps {
  children: ReactNode;
  roleName?: string;
  progressStep?: number;
  totalSteps?: number;
}

export function FocusedFlowLayout({
  children,
  roleName,
  progressStep,
  totalSteps = 5,
}: FocusedFlowLayoutProps) {
  return (
    <div className="w-full px-4 md:px-6 mx-auto max-w-[90vw] md:max-w-[90vw] lg:max-w-[700px] xl:max-w-[800px] py-8 lg:py-10 xl:py-16">
      {(roleName || progressStep !== undefined) && (
        <div className="mb-6 space-y-3">
          {roleName && (
            <span className="inline-flex items-center gap-2 px-4 py-2 bg-accent rounded-full text-sm font-medium">
              {roleName}
            </span>
          )}
          {progressStep !== undefined && (
            <div className="flex gap-1.5">
              {Array.from({ length: totalSteps }, (_, i) => {
                const step = i + 1;
                const isComplete = step < progressStep;
                const isCurrent = step === progressStep;
                return (
                  <div
                    key={step}
                    className={`h-1 flex-1 rounded-full ${
                      isComplete
                        ? 'bg-primary'
                        : isCurrent
                          ? 'bg-gradient-to-r from-primary to-primary/40'
                          : 'bg-border'
                    }`}
                  />
                );
              })}
            </div>
          )}
        </div>
      )}
      {children}
    </div>
  );
}
