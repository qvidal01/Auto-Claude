import { create } from "zustand";
import type { Task } from "@auto-claude/types";

/**
 * Sidebar view types matching the Electron app's navigation.
 * All 13 views from the Electron app plus settings.
 */
export type SidebarView =
  | "kanban"
  | "terminals"
  | "roadmap"
  | "context"
  | "ideation"
  | "insights"
  | "github-issues"
  | "github-prs"
  | "gitlab-issues"
  | "gitlab-merge-requests"
  | "changelog"
  | "worktrees"
  | "agent-tools"
  | "settings";

/** Keyboard shortcut definition */
export interface KeyboardShortcut {
  key: string;
  modifiers?: ("ctrl" | "shift" | "alt" | "meta")[];
  action: string;
  description: string;
}

/** Default keyboard shortcuts */
const DEFAULT_SHORTCUTS: KeyboardShortcut[] = [
  {
    key: "k",
    modifiers: ["meta"],
    action: "command-palette",
    description: "Open command palette",
  },
  {
    key: "n",
    modifiers: ["meta"],
    action: "new-task",
    description: "Create new task",
  },
  {
    key: ",",
    modifiers: ["meta"],
    action: "open-settings",
    description: "Open settings",
  },
  {
    key: "Escape",
    action: "close-modal",
    description: "Close current modal",
  },
];

interface UIState {
  activeView: SidebarView;
  sidebarCollapsed: boolean;
  selectedTask: Task | null;

  // Modal states
  isNewTaskDialogOpen: boolean;
  isSettingsDialogOpen: boolean;
  isOnboardingOpen: boolean;
  isCommandPaletteOpen: boolean;
  isDeleteConfirmOpen: boolean;
  deleteConfirmTaskId: string | null;
  isGitHubSetupOpen: boolean;
  isGitLabSetupOpen: boolean;

  // Keyboard shortcuts
  shortcuts: KeyboardShortcut[];

  // Actions
  setActiveView: (view: SidebarView) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
  setSelectedTask: (task: Task | null) => void;

  // Modal actions
  setNewTaskDialogOpen: (open: boolean) => void;
  setSettingsDialogOpen: (open: boolean) => void;
  setOnboardingOpen: (open: boolean) => void;
  setCommandPaletteOpen: (open: boolean) => void;
  openDeleteConfirm: (taskId: string) => void;
  closeDeleteConfirm: () => void;
  setGitHubSetupOpen: (open: boolean) => void;
  setGitLabSetupOpen: (open: boolean) => void;
  closeAllModals: () => void;

  // Keyboard shortcut actions
  setShortcuts: (shortcuts: KeyboardShortcut[]) => void;
  getShortcutForAction: (action: string) => KeyboardShortcut | undefined;
}

export const useUIStore = create<UIState>((set, get) => ({
  activeView: "kanban",
  sidebarCollapsed: false,
  selectedTask: null,

  // Modal states
  isNewTaskDialogOpen: false,
  isSettingsDialogOpen: false,
  isOnboardingOpen: false,
  isCommandPaletteOpen: false,
  isDeleteConfirmOpen: false,
  deleteConfirmTaskId: null,
  isGitHubSetupOpen: false,
  isGitLabSetupOpen: false,

  // Keyboard shortcuts
  shortcuts: DEFAULT_SHORTCUTS,

  // Actions
  setActiveView: (view) => set({ activeView: view }),

  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  setSelectedTask: (task) => set({ selectedTask: task }),

  // Modal actions
  setNewTaskDialogOpen: (open) => set({ isNewTaskDialogOpen: open }),
  setSettingsDialogOpen: (open) => set({ isSettingsDialogOpen: open }),
  setOnboardingOpen: (open) => set({ isOnboardingOpen: open }),
  setCommandPaletteOpen: (open) => set({ isCommandPaletteOpen: open }),

  openDeleteConfirm: (taskId) =>
    set({ isDeleteConfirmOpen: true, deleteConfirmTaskId: taskId }),

  closeDeleteConfirm: () =>
    set({ isDeleteConfirmOpen: false, deleteConfirmTaskId: null }),

  setGitHubSetupOpen: (open) => set({ isGitHubSetupOpen: open }),
  setGitLabSetupOpen: (open) => set({ isGitLabSetupOpen: open }),

  closeAllModals: () =>
    set({
      isNewTaskDialogOpen: false,
      isSettingsDialogOpen: false,
      isOnboardingOpen: false,
      isCommandPaletteOpen: false,
      isDeleteConfirmOpen: false,
      deleteConfirmTaskId: null,
      isGitHubSetupOpen: false,
      isGitLabSetupOpen: false,
    }),

  // Keyboard shortcut actions
  setShortcuts: (shortcuts) => set({ shortcuts }),

  getShortcutForAction: (action) => {
    return get().shortcuts.find((s) => s.action === action);
  },
}));
