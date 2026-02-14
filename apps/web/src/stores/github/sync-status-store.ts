import { create } from "zustand";
import type { GitHubSyncStatus } from "@auto-claude/types";
interface SyncStatusState {
  // Sync status
  syncStatus: GitHubSyncStatus | null;
  connectionError: string | null;

  // Actions
  setSyncStatus: (status: GitHubSyncStatus | null) => void;
  setConnectionError: (error: string | null) => void;
  clearSyncStatus: () => void;

  // Selectors
  isConnected: () => boolean;
  getRepoFullName: () => string | null;
}

export const useSyncStatusStore = create<SyncStatusState>((set, get) => ({
  syncStatus: null,
  connectionError: null,

  setSyncStatus: (syncStatus) => set({ syncStatus, connectionError: null }),

  setConnectionError: (connectionError) => set({ connectionError }),

  clearSyncStatus: () =>
    set({
      syncStatus: null,
      connectionError: null,
    }),

  isConnected: () => {
    const { syncStatus } = get();
    return syncStatus?.connected ?? false;
  },

  getRepoFullName: () => {
    const { syncStatus } = get();
    return syncStatus?.repoFullName ?? null;
  },
}));

/**
 * Check GitHub connection status
 */
export async function checkGitHubConnection(
  projectId: string,
): Promise<GitHubSyncStatus | null> {
  const store = useSyncStatusStore.getState();

  try {
    // TODO: Wire up to apiClient once the endpoint is available
    void projectId;
    return null;
  } catch (error) {
    store.setConnectionError(
      error instanceof Error ? error.message : "Unknown error",
    );
    return null;
  }
}
