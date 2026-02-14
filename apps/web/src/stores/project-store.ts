import { create } from "zustand";
import type { Project } from "@auto-claude/types";
import { apiClient } from "@/lib/data";

// localStorage keys for persisting tab state
const TAB_STATE_KEY = "auto-claude-tab-state";

interface TabState {
  openProjectIds: string[];
  activeProjectId: string | null;
}

interface ProjectState {
  projects: Project[];
  selectedProjectId: string | null;
  activeProjectId: string | null;
  openProjectIds: string[];
  tabOrder: string[];
  isLoading: boolean;
  isInitialized: boolean;
  error: string | null;

  // Actions
  setProjects: (projects: Project[]) => void;
  addProject: (project: Project) => void;
  removeProject: (projectId: string) => void;
  updateProject: (projectId: string, updates: Partial<Project>) => void;
  selectProject: (id: string | null) => void;
  setActiveProject: (id: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Tab management
  openProjectTab: (id: string) => void;
  closeProjectTab: (id: string) => void;
  reorderTabs: (oldIndex: number, newIndex: number) => void;
  restoreTabState: () => void;

  // Selectors
  getSelectedProject: () => Project | undefined;
  getActiveProject: () => Project | undefined;
  getProjectTabs: () => Project[];
  getOpenProjects: () => Project[];
}

function saveTabState(state: TabState): void {
  try {
    localStorage.setItem(TAB_STATE_KEY, JSON.stringify(state));
  } catch {
    // localStorage may be unavailable
  }
}

function loadTabState(): TabState | null {
  try {
    const raw = localStorage.getItem(TAB_STATE_KEY);
    if (raw) return JSON.parse(raw) as TabState;
  } catch {
    // Ignore parse errors
  }
  return null;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  selectedProjectId: null,
  activeProjectId: null,
  openProjectIds: [],
  tabOrder: [],
  isLoading: false,
  isInitialized: false,
  error: null,

  setProjects: (projects) => set({ projects }),

  addProject: (project) =>
    set((state) => ({
      projects: [...state.projects, project],
    })),

  removeProject: (projectId) =>
    set((state) => {
      const newOpenIds = state.openProjectIds.filter((id) => id !== projectId);
      const newTabOrder = state.tabOrder.filter((id) => id !== projectId);
      const isActive = state.activeProjectId === projectId;
      const newActiveId = isActive
        ? newTabOrder[0] ?? null
        : state.activeProjectId;

      saveTabState({ openProjectIds: newOpenIds, activeProjectId: newActiveId });

      return {
        projects: state.projects.filter((p) => p.id !== projectId),
        selectedProjectId:
          state.selectedProjectId === projectId ? null : state.selectedProjectId,
        activeProjectId: newActiveId,
        openProjectIds: newOpenIds,
        tabOrder: newTabOrder,
      };
    }),

  updateProject: (projectId, updates) =>
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === projectId ? { ...p, ...updates } : p,
      ),
    })),

  selectProject: (id) => set({ selectedProjectId: id }),

  setActiveProject: (id) => {
    set({ activeProjectId: id, selectedProjectId: id });
    const state = get();
    saveTabState({
      openProjectIds: state.openProjectIds,
      activeProjectId: id,
    });
  },

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  openProjectTab: (id) =>
    set((state) => {
      if (state.openProjectIds.includes(id)) {
        saveTabState({ openProjectIds: state.openProjectIds, activeProjectId: id });
        return { activeProjectId: id, selectedProjectId: id };
      }
      const newOpenIds = [...state.openProjectIds, id];
      const newTabOrder = state.tabOrder.includes(id)
        ? state.tabOrder
        : [...state.tabOrder, id];

      saveTabState({ openProjectIds: newOpenIds, activeProjectId: id });

      return {
        openProjectIds: newOpenIds,
        tabOrder: newTabOrder,
        activeProjectId: id,
        selectedProjectId: id,
      };
    }),

  closeProjectTab: (id) =>
    set((state) => {
      const newOpenIds = state.openProjectIds.filter((pid) => pid !== id);
      const newTabOrder = state.tabOrder.filter((pid) => pid !== id);
      const newActiveId =
        state.activeProjectId === id
          ? newTabOrder[0] ?? null
          : state.activeProjectId;

      saveTabState({ openProjectIds: newOpenIds, activeProjectId: newActiveId });

      return {
        openProjectIds: newOpenIds,
        tabOrder: newTabOrder,
        activeProjectId: newActiveId,
        selectedProjectId: newActiveId,
      };
    }),

  reorderTabs: (oldIndex, newIndex) =>
    set((state) => {
      const newOrder = [...state.tabOrder];
      const [removed] = newOrder.splice(oldIndex, 1);
      newOrder.splice(newIndex, 0, removed);
      saveTabState({
        openProjectIds: newOrder,
        activeProjectId: state.activeProjectId,
      });
      return { tabOrder: newOrder, openProjectIds: newOrder };
    }),

  restoreTabState: () => {
    const saved = loadTabState();
    if (saved) {
      const state = get();
      // Only restore IDs that match existing projects
      const validIds = new Set(state.projects.map((p) => p.id));
      const openIds = saved.openProjectIds.filter((id) => validIds.has(id));
      const activeId =
        saved.activeProjectId && validIds.has(saved.activeProjectId)
          ? saved.activeProjectId
          : openIds[0] ?? null;

      set({
        openProjectIds: openIds,
        tabOrder: openIds,
        activeProjectId: activeId,
        selectedProjectId: activeId,
      });
    }
  },

  getSelectedProject: () => {
    const state = get();
    return state.projects.find((p) => p.id === state.selectedProjectId);
  },

  getActiveProject: () => {
    const state = get();
    return state.projects.find((p) => p.id === state.activeProjectId);
  },

  getProjectTabs: () => {
    const state = get();
    return state.tabOrder
      .map((id) => state.projects.find((p) => p.id === id))
      .filter((p): p is Project => p !== undefined);
  },

  getOpenProjects: () => {
    const state = get();
    return state.projects.filter((p) => state.openProjectIds.includes(p.id));
  },
}));

/** Load projects from API and restore tab state */
export async function loadProjects() {
  useProjectStore.setState({ isLoading: true, error: null });
  try {
    const result = await apiClient.getProjects();
    useProjectStore.setState({
      projects: result.projects as Project[],
      isLoading: false,
      isInitialized: true,
    });

    // Restore tab state from localStorage
    useProjectStore.getState().restoreTabState();

    // Auto-select first project if none selected
    const state = useProjectStore.getState();
    if (!state.activeProjectId && result.projects.length > 0) {
      const firstProject = result.projects[0] as Project;
      useProjectStore.getState().openProjectTab(firstProject.id);
    }
  } catch (error) {
    useProjectStore.setState({
      isLoading: false,
      isInitialized: true,
      error:
        error instanceof Error ? error.message : "Failed to load projects",
    });
  }
}
