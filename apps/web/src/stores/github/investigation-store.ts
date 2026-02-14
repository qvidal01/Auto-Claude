import { create } from "zustand";
import type {
  GitHubInvestigationStatus,
  GitHubInvestigationResult,
} from "@auto-claude/types";
import { apiClient } from "@/lib/data";

interface InvestigationState {
  // Investigation state
  investigationStatus: GitHubInvestigationStatus;
  lastInvestigationResult: GitHubInvestigationResult | null;

  // Actions
  setInvestigationStatus: (status: GitHubInvestigationStatus) => void;
  setInvestigationResult: (result: GitHubInvestigationResult | null) => void;
  clearInvestigation: () => void;
}

export const useInvestigationStore = create<InvestigationState>((set) => ({
  investigationStatus: {
    phase: "idle",
    progress: 0,
    message: "",
  },
  lastInvestigationResult: null,

  setInvestigationStatus: (investigationStatus) =>
    set({ investigationStatus }),

  setInvestigationResult: (lastInvestigationResult) =>
    set({ lastInvestigationResult }),

  clearInvestigation: () =>
    set({
      investigationStatus: { phase: "idle", progress: 0, message: "" },
      lastInvestigationResult: null,
    }),
}));

/**
 * Start investigating a GitHub issue
 */
export async function investigateGitHubIssue(
  projectId: string,
  issueNumber: number,
  selectedCommentIds?: number[],
): Promise<void> {
  const store = useInvestigationStore.getState();
  store.setInvestigationStatus({
    phase: "fetching",
    issueNumber,
    progress: 0,
    message: "Starting investigation...",
  });
  store.setInvestigationResult(null);

  try {
    // Note: selectedCommentIds not yet supported by the REST endpoint
    void selectedCommentIds;
    const result = await apiClient.investigateGitHubIssue(
      projectId,
      issueNumber,
    );
    const investigation = result.investigation as GitHubInvestigationResult | null;
    if (investigation) {
      store.setInvestigationResult(investigation);
      store.setInvestigationStatus({
        phase: "complete",
        issueNumber,
        progress: 100,
        message: "Investigation complete",
      });
    } else {
      store.setInvestigationStatus({
        phase: "error",
        issueNumber,
        progress: 0,
        message: "Investigation failed",
      });
    }
  } catch (error) {
    store.setInvestigationStatus({
      phase: "error",
      issueNumber,
      progress: 0,
      message:
        error instanceof Error ? error.message : "Investigation failed",
    });
  }
}
