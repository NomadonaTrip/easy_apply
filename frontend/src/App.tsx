import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
import { RegisterPage } from '@/pages/RegisterPage';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { RolesPage } from '@/pages/RolesPage';
import { ExperiencePage } from '@/pages/ExperiencePage';
import { NewApplicationPage } from '@/pages/applications/NewApplicationPage';
import { KeywordsPage } from '@/pages/applications/KeywordsPage';
import { ApplicationDetailPage } from '@/pages/applications/ApplicationDetailPage';
import { ResearchPage } from '@/pages/applications/ResearchPage';
import { ReviewPage } from '@/pages/applications/ReviewPage';
import { ContextPage } from '@/pages/applications/ContextPage';
import { ExportPage } from '@/pages/applications/ExportPage';
import { SSETestPage } from '@/pages/SSETestPage';
import { AppShell } from '@/components/layout/AppShell';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { useAuthStore } from '@/stores/authStore';

function AppRoutes() {
  const { checkAuth, isLoading } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[100vh] min-h-[100dvh]">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <AppShell>
      <Routes>
        {/* Public routes */}
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />

        {/* Protected routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/roles"
          element={
            <ProtectedRoute>
              <RolesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/experience"
          element={
            <ProtectedRoute>
              <ExperiencePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/applications/new"
          element={
            <ProtectedRoute>
              <NewApplicationPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/applications/:id"
          element={
            <ProtectedRoute>
              <ApplicationDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/applications/:id/keywords"
          element={
            <ProtectedRoute>
              <KeywordsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/applications/:id/research"
          element={
            <ProtectedRoute>
              <ResearchPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/applications/:id/review"
          element={
            <ProtectedRoute>
              <ReviewPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/applications/:id/context"
          element={
            <ProtectedRoute>
              <ContextPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/applications/:id/export"
          element={
            <ProtectedRoute>
              <ExportPage />
            </ProtectedRoute>
          }
        />

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* 404 fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AppShell>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <TooltipProvider>
          <Routes>
            {/* Temporary: SSE spike test page (Story 0-5) — outside AppShell to skip auth check */}
            <Route path="/test/sse" element={<SSETestPage />} />
            <Route path="*" element={<AppRoutes />} />
          </Routes>
          <Toaster />
        </TooltipProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
