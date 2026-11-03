import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'

import { AppLayout } from '@/components/layout/app-layout'
import { Toaster } from '@/components/ui/sonner'
import { AgentsPage } from '@/features/agents/agents-page'
import { AnalyticsPage } from '@/features/analytics/analytics-page'
import { ApprovalsPage } from '@/features/approvals/approvals-page'
import { DashboardPage } from '@/features/dashboard/dashboard-page'
import { HistoryPage } from '@/features/history/history-page'
import { ProjectsPage } from '@/features/projects/projects-page'
import { SettingsPage } from '@/features/settings/settings-page'
import { TasksPage } from '@/features/tasks/tasks-page'
import { WorkflowPage } from '@/features/workflow/workflow-page'
import { CurrentWorkspaceRedirect, WorkspacePage } from '@/features/workspace/workspace-page'
import { ShellProvider } from '@/hooks/use-shell'

import './index.css'

const router = createBrowserRouter([
  {
    element: (
      <ShellProvider>
        <AppLayout />
      </ShellProvider>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'projects', element: <ProjectsPage /> },
      { path: 'projects/:projectId', element: <WorkspacePage /> },
      { path: 'workspace', element: <CurrentWorkspaceRedirect /> },
      { path: 'agents', element: <AgentsPage /> },
      { path: 'workflow', element: <WorkflowPage /> },
      { path: 'tasks', element: <TasksPage /> },
      { path: 'approvals', element: <ApprovalsPage /> },
      { path: 'history', element: <HistoryPage /> },
      { path: 'analytics', element: <AnalyticsPage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: '*', element: <Navigate to="/dashboard" replace /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
    <Toaster richColors theme="dark" />
  </StrictMode>,
)
