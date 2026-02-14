import { create } from "zustand";
import type { Project } from "@auto-claude/types";
import { apiClient } from "@/lib/data";

interface ProjectState {
  projects: Project[];
  selectedProjectId: string | null;
  activeProjectId: string | null;
  openProjectIds: string[];
  isLoading: boolean;
  error: string | null;

  // Actions
  setProjects: (projects: Project[]) => void;
  selectProject: (id: string) => void;
  setActiveProject: (id: string) => void;
  openProjectTab: (id: string) => void;
  closeProjectTab: (id: string) => void;
  reorderTabs: (oldIndex: number, newIndex: number) => void;
  getProjectTabs: () => Project[];
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  selectedProjectId: null,
  activeProjectId: null,
  openProjectIds: [],
  isLoading: false,
  error: null,

  setProjects: (projects) => set({ projects }),

  selectProject: (id) => set({ selectedProjectId: id }),

  setActiveProject: (id) =>
    set({ activeProjectId: id, selectedProjectId: id }),

  openProjectTab: (id) =>
    set((state) => {
      if (state.openProjectIds.includes(id)) {
        return { activeProjectId: id, selectedProjectId: id };
      }
      return {
        openProjectIds: [...state.openProjectIds, id],
        activeProjectId: id,
        selectedProjectId: id,
      };
    }),

  closeProjectTab: (id) =>
    set((state) => {
      const newOpenIds = state.openProjectIds.filter((pid) => pid !== id);
      const newActiveId =
        state.activeProjectId === id
          ? newOpenIds[newOpenIds.length - 1] ?? null
          : state.activeProjectId;
      return {
        openProjectIds: newOpenIds,
        activeProjectId: newActiveId,
        selectedProjectId: newActiveId,
      };
    }),

  reorderTabs: (oldIndex, newIndex) =>
    set((state) => {
      const newOrder = [...state.openProjectIds];
      const [removed] = newOrder.splice(oldIndex, 1);
      newOrder.splice(newIndex, 0, removed);
      return { openProjectIds: newOrder };
    }),

  getProjectTabs: () => {
    const state = get();
    return state.openProjectIds
      .map((id) => state.projects.find((p) => p.id === id))
      .filter((p): p is Project => p !== undefined);
  },
}));

export async function loadProjects() {
  useProjectStore.setState({ isLoading: true, error: null });
  try {
    const result = await apiClient.getProjects();
    useProjectStore.setState({
      projects: result.projects as Project[],
      isLoading: false,
    });

    // Auto-select first project if none selected
    const state = useProjectStore.getState();
    if (!state.activeProjectId && result.projects.length > 0) {
      const firstProject = result.projects[0] as Project;
      useProjectStore.getState().openProjectTab(firstProject.id);
    }
  } catch (error) {
    useProjectStore.setState({
      isLoading: false,
      error: error instanceof Error ? error.message : "Failed to load projects",
    });
  }
}
