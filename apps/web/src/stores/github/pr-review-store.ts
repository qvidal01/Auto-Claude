import { create } from "zustand";
import type {
  ChecksStatus,
  ReviewsStatus,
  MergeableState,
} from "@auto-claude/types";

/**
 * PR review progress event from the backend.
 */
export interface PRReviewProgress {
  prNumber: number;
  phase: string;
  progress: number;
  message: string;
}

/**
 * PR review result from the backend.
 */
export interface PRReviewResult {
  prNumber: number;
  summary: string;
  findings: Array<{
    severity: "critical" | "warning" | "suggestion" | "praise";
    file: string;
    line?: number;
    message: string;
  }>;
  approved: boolean;
  error?: string;
}

/**
 * New commits check result.
 */
export interface NewCommitsCheck {
  hasNewCommits: boolean;
  newCommitCount: number;
  lastReviewedCommit: string | null;
}

/**
 * PR review state for a single PR
 */
interface PRReviewState {
  prNumber: number;
  projectId: string;
  isReviewing: boolean;
  startedAt: string | null;
  progress: PRReviewProgress | null;
  result: PRReviewResult | null;
  previousResult: PRReviewResult | null;
  error: string | null;
  newCommitsCheck: NewCommitsCheck | null;
  checksStatus: ChecksStatus | null;
  reviewsStatus: ReviewsStatus | null;
  mergeableState: MergeableState | null;
  lastPolled: string | null;
}

interface PRReviewStoreState {
  // Key: `${projectId}:${prNumber}`
  prReviews: Record<string, PRReviewState>;

  // Actions
  startPRReview: (projectId: string, prNumber: number) => void;
  startFollowupReview: (projectId: string, prNumber: number) => void;
  setPRReviewProgress: (
    projectId: string,
    progress: PRReviewProgress,
  ) => void;
  setPRReviewResult: (projectId: string, result: PRReviewResult) => void;
  setPRReviewError: (
    projectId: string,
    prNumber: number,
    error: string,
  ) => void;
  setNewCommitsCheck: (
    projectId: string,
    prNumber: number,
    check: NewCommitsCheck,
  ) => void;
  clearPRReview: (projectId: string, prNumber: number) => void;
  setPRStatus: (
    projectId: string,
    prNumber: number,
    status: {
      checksStatus: ChecksStatus;
      reviewsStatus: ReviewsStatus;
      mergeableState: MergeableState;
      lastPolled: string;
    },
  ) => void;
  clearPRStatus: (projectId: string, prNumber: number) => void;

  // Selectors
  getPRReviewState: (
    projectId: string,
    prNumber: number,
  ) => PRReviewState | null;
  getActivePRReviews: (projectId: string) => PRReviewState[];
}

function makeKey(projectId: string, prNumber: number): string {
  return `${projectId}:${prNumber}`;
}

function createMinimalState(
  projectId: string,
  prNumber: number,
  overrides?: Partial<PRReviewState>,
): PRReviewState {
  return {
    prNumber,
    projectId,
    isReviewing: false,
    startedAt: null,
    progress: null,
    result: null,
    previousResult: null,
    error: null,
    newCommitsCheck: null,
    checksStatus: null,
    reviewsStatus: null,
    mergeableState: null,
    lastPolled: null,
    ...overrides,
  };
}

export const usePRReviewStore = create<PRReviewStoreState>((set, get) => ({
  prReviews: {},

  startPRReview: (projectId, prNumber) =>
    set((state) => {
      const key = makeKey(projectId, prNumber);
      const existing = state.prReviews[key];
      return {
        prReviews: {
          ...state.prReviews,
          [key]: createMinimalState(projectId, prNumber, {
            isReviewing: true,
            startedAt: new Date().toISOString(),
            newCommitsCheck: existing?.newCommitsCheck ?? null,
            checksStatus: existing?.checksStatus ?? null,
            reviewsStatus: existing?.reviewsStatus ?? null,
            mergeableState: existing?.mergeableState ?? null,
            lastPolled: existing?.lastPolled ?? null,
          }),
        },
      };
    }),

  startFollowupReview: (projectId, prNumber) =>
    set((state) => {
      const key = makeKey(projectId, prNumber);
      const existing = state.prReviews[key];
      return {
        prReviews: {
          ...state.prReviews,
          [key]: createMinimalState(projectId, prNumber, {
            isReviewing: true,
            startedAt: new Date().toISOString(),
            previousResult: existing?.result ?? null,
            newCommitsCheck: existing?.newCommitsCheck ?? null,
            checksStatus: existing?.checksStatus ?? null,
            reviewsStatus: existing?.reviewsStatus ?? null,
            mergeableState: existing?.mergeableState ?? null,
            lastPolled: existing?.lastPolled ?? null,
          }),
        },
      };
    }),

  setPRReviewProgress: (projectId, progress) =>
    set((state) => {
      const key = makeKey(projectId, progress.prNumber);
      const existing = state.prReviews[key];
      return {
        prReviews: {
          ...state.prReviews,
          [key]: {
            ...(existing ??
              createMinimalState(projectId, progress.prNumber)),
            isReviewing: true,
            progress,
            error: null,
          },
        },
      };
    }),

  setPRReviewResult: (projectId, result) =>
    set((state) => {
      const key = makeKey(projectId, result.prNumber);
      const existing = state.prReviews[key];
      return {
        prReviews: {
          ...state.prReviews,
          [key]: {
            ...(existing ??
              createMinimalState(projectId, result.prNumber)),
            isReviewing: false,
            progress: null,
            result,
            error: result.error ?? null,
            newCommitsCheck: null,
          },
        },
      };
    }),

  setPRReviewError: (projectId, prNumber, error) =>
    set((state) => {
      const key = makeKey(projectId, prNumber);
      const existing = state.prReviews[key];
      return {
        prReviews: {
          ...state.prReviews,
          [key]: {
            ...(existing ?? createMinimalState(projectId, prNumber)),
            isReviewing: false,
            progress: null,
            error,
          },
        },
      };
    }),

  setNewCommitsCheck: (projectId, prNumber, check) =>
    set((state) => {
      const key = makeKey(projectId, prNumber);
      const existing = state.prReviews[key];
      return {
        prReviews: {
          ...state.prReviews,
          [key]: {
            ...(existing ?? createMinimalState(projectId, prNumber)),
            newCommitsCheck: check,
          },
        },
      };
    }),

  clearPRReview: (projectId, prNumber) =>
    set((state) => {
      const key = makeKey(projectId, prNumber);
      const { [key]: _, ...rest } = state.prReviews;
      return { prReviews: rest };
    }),

  setPRStatus: (projectId, prNumber, status) =>
    set((state) => {
      const key = makeKey(projectId, prNumber);
      const existing = state.prReviews[key];
      return {
        prReviews: {
          ...state.prReviews,
          [key]: {
            ...(existing ?? createMinimalState(projectId, prNumber)),
            checksStatus: status.checksStatus,
            reviewsStatus: status.reviewsStatus,
            mergeableState: status.mergeableState,
            lastPolled: status.lastPolled,
          },
        },
      };
    }),

  clearPRStatus: (projectId, prNumber) =>
    set((state) => {
      const key = makeKey(projectId, prNumber);
      const existing = state.prReviews[key];
      if (!existing) return state;
      return {
        prReviews: {
          ...state.prReviews,
          [key]: {
            ...existing,
            checksStatus: null,
            reviewsStatus: null,
            mergeableState: null,
            lastPolled: null,
          },
        },
      };
    }),

  getPRReviewState: (projectId, prNumber) => {
    const key = makeKey(projectId, prNumber);
    return get().prReviews[key] ?? null;
  },

  getActivePRReviews: (projectId) => {
    return Object.values(get().prReviews).filter(
      (review) => review.projectId === projectId && review.isReviewing,
    );
  },
}));
