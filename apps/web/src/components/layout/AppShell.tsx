"use client";

import { useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { ProjectTabBar } from "./ProjectTabBar";
import { useUIStore } from "@/stores/ui-store";
import { useProjectStore } from "@/stores/project-store";
import { useTaskStore } from "@/stores/task-store";
import { loadTasks } from "@/stores/task-store";
import { KanbanBoard } from "@/components/kanban/KanbanBoard";
import { RoadmapView } from "@/components/roadmap/RoadmapView";
import { IdeationView } from "@/components/ideation/IdeationView";
import { InsightsView } from "@/components/insights/InsightsView";
import { ChangelogView } from "@/components/changelog/ChangelogView";
import { ContextView } from "@/components/context/ContextView";
import { GitHubIssuesView } from "@/components/github/GitHubIssuesView";
import { GitHubPRsView } from "@/components/github/GitHubPRsView";
import { SettingsView } from "@/components/settings/SettingsView";
import { WelcomeScreen } from "./WelcomeScreen";

export function AppShell() {
  const activeView = useUIStore((s) => s.activeView);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);
  const projects = useProjectStore((s) => s.projects);

  const currentProjectId = activeProjectId || selectedProjectId;
  const selectedProject = projects.find((p) => p.id === currentProjectId);

  // Load tasks when project changes
  useEffect(() => {
    if (currentProjectId) {
      loadTasks(currentProjectId);
    } else {
      useTaskStore.getState().clearTasks();
    }
  }, [currentProjectId]);

  // Apply theme
  useEffect(() => {
    const root = document.documentElement;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");

    const applyTheme = () => {
      // Default to dark for now
      if (prefersDark.matches) {
        root.classList.add("dark");
      } else {
        root.classList.remove("dark");
      }
    };

    applyTheme();
    prefersDark.addEventListener("change", applyTheme);
    return () => prefersDark.removeEventListener("change", applyTheme);
  }, []);

  const renderContent = () => {
    if (!selectedProject) {
      return <WelcomeScreen />;
    }

    switch (activeView) {
      case "kanban":
        return <KanbanBoard />;
      case "roadmap":
        return <RoadmapView projectId={currentProjectId!} />;
      case "ideation":
        return <IdeationView projectId={currentProjectId!} />;
      case "insights":
        return <InsightsView projectId={currentProjectId!} />;
      case "changelog":
        return <ChangelogView projectId={currentProjectId!} />;
      case "context":
        return <ContextView projectId={currentProjectId!} />;
      case "github-issues":
        return <GitHubIssuesView projectId={currentProjectId!} />;
      case "github-prs":
        return <GitHubPRsView projectId={currentProjectId!} />;
      case "settings":
        return <SettingsView />;
      default:
        return <KanbanBoard />;
    }
  };

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Project Tabs */}
        <ProjectTabBar />

        {/* Main content area */}
        <main className="flex-1 overflow-hidden">{renderContent()}</main>
      </div>
    </div>
  );
}
