import { create } from 'zustand';
import type { ClaudeUsageSnapshot } from '../../shared/types';

interface UsageState {
  // Usage snapshot data
  usage: ClaudeUsageSnapshot | null;

  // Loading and error states
  isLoading: boolean;
  error: string | null;

  // Actions
  setUsage: (snapshot: ClaudeUsageSnapshot) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearUsage: () => void;
}

export const useUsageStore = create<UsageState>((set) => ({
  usage: null,
  isLoading: false,
  error: null,

  setUsage: (snapshot: ClaudeUsageSnapshot) => {
    set({
      usage: snapshot,
      error: null
    });
  },

  setLoading: (loading: boolean) => {
    set({ isLoading: loading });
  },

  setError: (error: string | null) => {
    set({ error });
  },

  clearUsage: () => {
    set({
      usage: null,
      error: null
    });
  },
}));

/**
 * Load usage data from the main process
 * Called on component mount to get initial usage state
 */
export async function loadUsageData(): Promise<void> {
  const store = useUsageStore.getState();
  store.setLoading(true);

  try {
    const result = await window.electronAPI.requestUsageUpdate();
    if (result.success && result.data) {
      store.setUsage(result.data);
    } else if (result.error) {
      store.setError(result.error);
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Failed to load usage data';
    store.setError(errorMessage);
  } finally {
    store.setLoading(false);
  }
}

/**
 * Subscribe to real-time usage updates from the main process
 * Returns unsubscribe function for cleanup
 */
export function subscribeToUsageUpdates(): () => void {
  const store = useUsageStore.getState();

  const unsubscribe = window.electronAPI.onUsageUpdated((snapshot: ClaudeUsageSnapshot) => {
    store.setUsage(snapshot);
  });

  return unsubscribe;
}
