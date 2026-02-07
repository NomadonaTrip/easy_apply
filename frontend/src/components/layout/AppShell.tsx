import type { ReactNode } from 'react';
import { Header } from './Header';
import { MobileBottomNav } from './MobileBottomNav';
import { useAuthStore } from '@/stores/authStore';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const { isAuthenticated } = useAuthStore();

  return (
    <div className="min-h-[100vh] min-h-[100dvh] flex flex-col">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-primary focus:text-primary-foreground focus:px-4 focus:py-2 focus:rounded-md"
      >
        Skip to main content
      </a>
      <Header />
      <main id="main-content" className={`flex-1 ${isAuthenticated ? 'pb-[72px] lg:pb-0' : ''}`}>
        {children}
      </main>
      {isAuthenticated && <MobileBottomNav />}
    </div>
  );
}
