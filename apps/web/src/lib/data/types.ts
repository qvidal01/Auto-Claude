/**
 * Data provider interfaces for dual-mode operation.
 *
 * The web app supports two data backends:
 * - Self-hosted: HTTP API calls to the local Python backend
 * - Cloud: Convex real-time hooks
 *
 * Components consume data through these interfaces, and the active
 * provider is determined at runtime by the CLOUD_MODE flag.
 */

import type {
  Task,
  TaskStatus,
  Project,
  ProjectEnvConfig,
} from "@auto-claude/types";

// ============================================
// Project Data
// ============================================

export interface ProjectData {
  projects: Project[];
  selectedProjectId: string | null;
  activeProjectId: string | null;
  isLoading: boolean;
}

export interface ProjectActions {
  loadProjects: () => Promise<void>;
  selectProject: (id: string) => void;
  setActiveProject: (id: string) => void;
}

// ============================================
// Task Data
// ============================================

export interface TaskData {
  tasks: Task[];
  isLoading: boolean;
  error: string | null;
}

export interface TaskActions {
  loadTasks: (projectId: string) => Promise<void>;
  updateTaskStatus: (taskId: string, status: TaskStatus) => Promise<void>;
  refreshTasks: (projectId: string) => Promise<void>;
}

// ============================================
// Settings Data
// ============================================

export interface AppSettings {
  theme: "light" | "dark" | "system";
  colorTheme?: string;
  language?: string;
  sidebarCollapsed?: boolean;
  onboardingCompleted?: boolean;
}

export interface SettingsData {
  settings: AppSettings;
  isLoading: boolean;
}

export interface SettingsActions {
  loadSettings: () => Promise<void>;
  saveSettings: (updates: Partial<AppSettings>) => Promise<void>;
}

// ============================================
// Project Env Config
// ============================================

export interface ProjectEnvData {
  envConfig: ProjectEnvConfig | null;
  isLoading: boolean;
}

export interface ProjectEnvActions {
  loadEnvConfig: (projectId: string) => Promise<void>;
  clearEnvConfig: () => void;
}

// ============================================
// Provider Interface
// ============================================

export interface DataProvider {
  mode: "cloud" | "self-hosted";
}
