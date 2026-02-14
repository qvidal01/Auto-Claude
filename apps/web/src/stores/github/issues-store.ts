import { create } from "zustand";
import type { GitHubIssue } from "@auto-claude/types";
import { apiClient } from "@/lib/data";

export type IssueFilterState = "open" | "closed" | "all";

interface IssuesState {
  // Data
  issues: GitHubIssue[];

  // UI State
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  selectedIssueNumber: number | null;
  filterState: IssueFilterState;

  // Pagination
  currentPage: number;
  hasMore: boolean;

  // Actions
  setIssues: (issues: GitHubIssue[]) => void;
  appendIssues: (issues: GitHubIssue[]) => void;
  addIssue: (issue: GitHubIssue) => void;
  updateIssue: (issueNumber: number, updates: Partial<GitHubIssue>) => void;
  setLoading: (loading: boolean) => void;
  setLoadingMore: (loading: boolean) => void;
  setError: (error: string | null) => void;
  selectIssue: (issueNumber: number | null) => void;
  setFilterState: (state: IssueFilterState) => void;
  setHasMore: (hasMore: boolean) => void;
  setCurrentPage: (page: number) => void;
  clearIssues: () => void;
  resetPagination: () => void;

  // Selectors
  getSelectedIssue: () => GitHubIssue | null;
  getFilteredIssues: () => GitHubIssue[];
  getOpenIssuesCount: () => number;
}

export const useIssuesStore = create<IssuesState>((set, get) => ({
  issues: [],
  isLoading: false,
  isLoadingMore: false,
  error: null,
  selectedIssueNumber: null,
  filterState: "open",
  currentPage: 1,
  hasMore: true,

  setIssues: (issues) => set({ issues, error: null }),

  appendIssues: (newIssues) =>
    set((state) => {
      const existingNumbers = new Set(state.issues.map((i) => i.number));
      const uniqueNewIssues = newIssues.filter(
        (i) => !existingNumbers.has(i.number),
      );
      return { issues: [...state.issues, ...uniqueNewIssues] };
    }),

  addIssue: (issue) =>
    set((state) => ({
      issues: [
        issue,
        ...state.issues.filter((i) => i.number !== issue.number),
      ],
    })),

  updateIssue: (issueNumber, updates) =>
    set((state) => ({
      issues: state.issues.map((issue) =>
        issue.number === issueNumber ? { ...issue, ...updates } : issue,
      ),
    })),

  setLoading: (isLoading) => set({ isLoading }),

  setLoadingMore: (isLoadingMore) => set({ isLoadingMore }),

  setError: (error) => set({ error, isLoading: false, isLoadingMore: false }),

  selectIssue: (selectedIssueNumber) => set({ selectedIssueNumber }),

  setFilterState: (filterState) => set({ filterState }),

  setHasMore: (hasMore) => set({ hasMore }),

  setCurrentPage: (currentPage) => set({ currentPage }),

  clearIssues: () =>
    set({
      issues: [],
      selectedIssueNumber: null,
      error: null,
      currentPage: 1,
      hasMore: true,
    }),

  resetPagination: () =>
    set({
      currentPage: 1,
      hasMore: true,
      selectedIssueNumber: null,
    }),

  // Selectors
  getSelectedIssue: () => {
    const { issues, selectedIssueNumber } = get();
    return issues.find((i) => i.number === selectedIssueNumber) || null;
  },

  getFilteredIssues: () => {
    const { issues, filterState } = get();
    if (filterState === "all") return issues;
    return issues.filter((issue) => issue.state === filterState);
  },

  getOpenIssuesCount: () => {
    const { issues } = get();
    return issues.filter((issue) => issue.state === "open").length;
  },
}));

/**
 * Load GitHub issues with pagination support
 */
export async function loadGitHubIssues(
  projectId: string,
  state?: IssueFilterState,
  fetchAll: boolean = false,
): Promise<void> {
  const store = useIssuesStore.getState();
  store.setLoading(true);
  store.setError(null);
  store.resetPagination();

  void state;
  void fetchAll;

  try {
    const result = await apiClient.getGitHubIssues(projectId);
    const issues = (result.issues ?? []) as GitHubIssue[];
    store.setIssues(issues);
    store.setHasMore(false);
    store.setCurrentPage(1);
  } catch (error) {
    store.setError(
      error instanceof Error ? error.message : "Unknown error",
    );
  } finally {
    store.setLoading(false);
  }
}

/**
 * Load more issues (for infinite scroll).
 * TODO: Wire up pagination once apiClient supports page params.
 */
export async function loadMoreGitHubIssues(
  _projectId: string,
  _state?: IssueFilterState,
): Promise<void> {
  // TODO: Implement pagination when backend supports it
}

/**
 * Load ALL issues (for search functionality)
 */
export async function loadAllGitHubIssues(
  projectId: string,
  state?: IssueFilterState,
): Promise<void> {
  return loadGitHubIssues(projectId, state, true);
}

/**
 * Import GitHub issues as tasks.
 * TODO: Wire up to apiClient once the endpoint is available.
 */
export async function importGitHubIssues(
  _projectId: string,
  _issueNumbers: number[],
): Promise<boolean> {
  // TODO: Implement when backend endpoint is available
  return false;
}
