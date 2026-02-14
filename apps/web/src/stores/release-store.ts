import { create } from "zustand";
import type {
  ReleaseableVersion,
  ReleasePreflightStatus,
  ReleaseProgress,
  CreateReleaseResult,
} from "@auto-claude/types";
interface ReleaseState {
  // Available versions from CHANGELOG.md
  releaseableVersions: ReleaseableVersion[];
  isLoadingVersions: boolean;

  // Selected version for release
  selectedVersion: string | null;

  // Pre-flight check state
  preflightStatus: ReleasePreflightStatus | null;
  isRunningPreflight: boolean;

  // Release options
  createAsDraft: boolean;
  markAsPrerelease: boolean;

  // Release progress
  releaseProgress: ReleaseProgress | null;
  isCreatingRelease: boolean;
  lastReleaseResult: CreateReleaseResult | null;

  // Error state
  error: string | null;

  // Actions
  setReleaseableVersions: (versions: ReleaseableVersion[]) => void;
  setIsLoadingVersions: (loading: boolean) => void;
  setSelectedVersion: (version: string | null) => void;
  setPreflightStatus: (status: ReleasePreflightStatus | null) => void;
  setIsRunningPreflight: (running: boolean) => void;
  setCreateAsDraft: (draft: boolean) => void;
  setMarkAsPrerelease: (prerelease: boolean) => void;
  setReleaseProgress: (progress: ReleaseProgress | null) => void;
  setIsCreatingRelease: (creating: boolean) => void;
  setLastReleaseResult: (result: CreateReleaseResult | null) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  releaseableVersions: [] as ReleaseableVersion[],
  isLoadingVersions: false,
  selectedVersion: null as string | null,
  preflightStatus: null as ReleasePreflightStatus | null,
  isRunningPreflight: false,
  createAsDraft: false,
  markAsPrerelease: false,
  releaseProgress: null as ReleaseProgress | null,
  isCreatingRelease: false,
  lastReleaseResult: null as CreateReleaseResult | null,
  error: null as string | null,
};

export const useReleaseStore = create<ReleaseState>((set) => ({
  ...initialState,

  setReleaseableVersions: (versions) =>
    set({ releaseableVersions: versions }),
  setIsLoadingVersions: (loading) => set({ isLoadingVersions: loading }),
  setSelectedVersion: (version) =>
    set({
      selectedVersion: version,
      preflightStatus: null,
      error: null,
    }),
  setPreflightStatus: (status) => set({ preflightStatus: status }),
  setIsRunningPreflight: (running) => set({ isRunningPreflight: running }),
  setCreateAsDraft: (draft) => set({ createAsDraft: draft }),
  setMarkAsPrerelease: (prerelease) =>
    set({ markAsPrerelease: prerelease }),
  setReleaseProgress: (progress) => set({ releaseProgress: progress }),
  setIsCreatingRelease: (creating) => set({ isCreatingRelease: creating }),
  setLastReleaseResult: (result) => set({ lastReleaseResult: result }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));

/**
 * Load releaseable versions from CHANGELOG.md
 */
export async function loadReleaseableVersions(
  projectId: string,
): Promise<void> {
  const store = useReleaseStore.getState();
  store.setIsLoadingVersions(true);
  store.setError(null);

  try {
    // TODO: Wire up to apiClient once the endpoint is available
    void projectId;
  } catch (error) {
    store.setError(
      error instanceof Error ? error.message : "Failed to load versions",
    );
  } finally {
    store.setIsLoadingVersions(false);
  }
}

/**
 * Run pre-flight checks for the selected version
 */
export async function runPreflightCheck(projectId: string): Promise<void> {
  const store = useReleaseStore.getState();
  const version = store.selectedVersion;

  if (!version) {
    store.setError("No version selected");
    return;
  }

  store.setIsRunningPreflight(true);
  store.setError(null);

  try {
    // TODO: Wire up to apiClient once the endpoint is available
    void projectId;
    void version;
  } catch (error) {
    store.setError(
      error instanceof Error
        ? error.message
        : "Failed to run pre-flight checks",
    );
  } finally {
    store.setIsRunningPreflight(false);
  }
}

/**
 * Get unreleased versions only
 */
export function getUnreleasedVersions(): ReleaseableVersion[] {
  const store = useReleaseStore.getState();
  return store.releaseableVersions.filter((v) => !v.isReleased);
}

/**
 * Get the currently selected version info
 */
export function getSelectedVersionInfo(): ReleaseableVersion | undefined {
  const store = useReleaseStore.getState();
  return store.releaseableVersions.find(
    (v) => v.version === store.selectedVersion,
  );
}

/**
 * Check if release button should be enabled
 */
export function canCreateRelease(): boolean {
  const store = useReleaseStore.getState();
  return (
    !!store.selectedVersion &&
    !!store.preflightStatus?.canRelease &&
    !store.isCreatingRelease
  );
}
