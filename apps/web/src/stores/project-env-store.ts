import { create } from "zustand";
import type { ProjectEnvConfig } from "@auto-claude/types";
import { apiClient } from "@/lib/data";

interface ProjectEnvState {
  // State
  envConfig: ProjectEnvConfig | null;
  projectId: string | null;
  isLoading: boolean;
  error: string | null;
  // Track the current pending request to handle race conditions
  currentRequestId: number;

  // Actions
  setEnvConfig: (
    projectId: string | null,
    config: ProjectEnvConfig | null,
  ) => void;
  setEnvConfigOnly: (
    projectId: string | null,
    config: ProjectEnvConfig | null,
  ) => void;
  clearEnvConfig: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  incrementRequestId: () => number;
}

export const useProjectEnvStore = create<ProjectEnvState>((set, get) => ({
  envConfig: null,
  projectId: null,
  isLoading: false,
  error: null,
  currentRequestId: 0,

  setEnvConfig: (projectId, envConfig) =>
    set({
      projectId,
      envConfig,
      error: null,
    }),

  setEnvConfigOnly: (projectId, envConfig) =>
    set({
      projectId,
      envConfig,
    }),

  clearEnvConfig: () =>
    set({
      envConfig: null,
      projectId: null,
      error: null,
    }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  incrementRequestId: () => {
    const newId = get().currentRequestId + 1;
    set({ currentRequestId: newId });
    return newId;
  },
}));

/**
 * Load project environment config from the backend API.
 * Handles race conditions when called rapidly for different projects.
 */
export async function loadProjectEnvConfig(
  projectId: string,
): Promise<ProjectEnvConfig | null> {
  const initialStore = useProjectEnvStore.getState();
  const requestId = initialStore.incrementRequestId();

  initialStore.setLoading(true);
  initialStore.setError(null);

  try {
    const result = await apiClient.getProjectEnv(projectId);

    const currentStore = useProjectEnvStore.getState();
    if (requestId !== currentStore.currentRequestId) {
      return null;
    }

    if (result.config) {
      currentStore.setEnvConfig(projectId, result.config);
      return result.config;
    } else {
      currentStore.setEnvConfigOnly(projectId, null);
      currentStore.setError("Failed to load environment config");
      return null;
    }
  } catch (error) {
    const currentStore = useProjectEnvStore.getState();
    if (requestId !== currentStore.currentRequestId) {
      return null;
    }

    currentStore.setEnvConfigOnly(projectId, null);
    currentStore.setError(
      error instanceof Error ? error.message : "Unknown error",
    );
    return null;
  } finally {
    const finalStore = useProjectEnvStore.getState();
    if (requestId === finalStore.currentRequestId) {
      finalStore.setLoading(false);
    }
  }
}

/**
 * Set project env config directly.
 */
export function setProjectEnvConfig(
  projectId: string,
  config: ProjectEnvConfig | null,
): void {
  const store = useProjectEnvStore.getState();
  store.setEnvConfig(projectId, config);
}

/**
 * Clear the project env config.
 */
export function clearProjectEnvConfig(): void {
  const store = useProjectEnvStore.getState();
  store.clearEnvConfig();
}
