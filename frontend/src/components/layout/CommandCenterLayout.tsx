import type { ReactNode } from 'react';
import { Sidebar } from './Sidebar';

interface CommandCenterLayoutProps {
  children: ReactNode;
}

export function CommandCenterLayout({ children }: CommandCenterLayoutProps) {
  return (
    <div className="flex flex-1 min-h-0">
      <Sidebar />
      <div className="flex-1 min-w-0 overflow-auto">
        {children}
      </div>
    </div>
  );
}
