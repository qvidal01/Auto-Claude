import { create } from "zustand";
import type {
  GitLabMRReviewProgress,
  GitLabMRReviewResult,
  GitLabNewCommitsCheck,
} from "@auto-claude/types";

/**
 * MR review state for a single MR
 */
interface MRReviewState {
  mrIid: number;
  projectId: string;
  isReviewing: boolean;
  progress: GitLabMRReviewProgress | null;
  result: GitLabMRReviewResult | null;
  error: string | null;
  newCommitsCheck: GitLabNewCommitsCheck | null;
}

interface MRReviewStoreState {
  // Key: `${projectId}:${mrIid}`
  mrReviews: Record<string, MRReviewState>;

  // Actions
  startMRReview: (projectId: string, mrIid: number) => void;
  setMRReviewProgress: (
    projectId: string,
    progress: GitLabMRReviewProgress,
  ) => void;
  setMRReviewResult: (
    projectId: string,
    result: GitLabMRReviewResult,
  ) => void;
  setMRReviewError: (
    projectId: string,
    mrIid: number,
    error: string,
  ) => void;
  setNewCommitsCheck: (
    projectId: string,
    mrIid: number,
    check: GitLabNewCommitsCheck,
  ) => void;
  clearMRReview: (projectId: string, mrIid: number) => void;

  // Selectors
  getMRReviewState: (
    projectId: string,
    mrIid: number,
  ) => MRReviewState | null;
  getActiveMRReviews: (projectId: string) => MRReviewState[];
}

function makeKey(projectId: string, mrIid: number): string {
  return `${projectId}:${mrIid}`;
}

function createMinimalState(
  projectId: string,
  mrIid: number,
  overrides?: Partial<MRReviewState>,
): MRReviewState {
  return {
    mrIid,
    projectId,
    isReviewing: false,
    progress: null,
    result: null,
    error: null,
    newCommitsCheck: null,
    ...overrides,
  };
}

export const useMRReviewStore = create<MRReviewStoreState>((set, get) => ({
  mrReviews: {},

  startMRReview: (projectId, mrIid) =>
    set((state) => {
      const key = makeKey(projectId, mrIid);
      const existing = state.mrReviews[key];
      return {
        mrReviews: {
          ...state.mrReviews,
          [key]: createMinimalState(projectId, mrIid, {
            isReviewing: true,
            newCommitsCheck: existing?.newCommitsCheck ?? null,
          }),
        },
      };
    }),

  setMRReviewProgress: (projectId, progress) =>
    set((state) => {
      const key = makeKey(projectId, progress.mrIid);
      const existing = state.mrReviews[key];
      return {
        mrReviews: {
          ...state.mrReviews,
          [key]: {
            ...(existing ??
              createMinimalState(projectId, progress.mrIid)),
            isReviewing: true,
            progress,
            error: null,
          },
        },
      };
    }),

  setMRReviewResult: (projectId, result) =>
    set((state) => {
      const key = makeKey(projectId, result.mrIid);
      return {
        mrReviews: {
          ...state.mrReviews,
          [key]: createMinimalState(projectId, result.mrIid, {
            result,
          }),
        },
      };
    }),

  setMRReviewError: (projectId, mrIid, error) =>
    set((state) => {
      const key = makeKey(projectId, mrIid);
      const existing = state.mrReviews[key];
      return {
        mrReviews: {
          ...state.mrReviews,
          [key]: {
            ...(existing ?? createMinimalState(projectId, mrIid)),
            isReviewing: false,
            progress: null,
            error,
          },
        },
      };
    }),

  setNewCommitsCheck: (projectId, mrIid, check) =>
    set((state) => {
      const key = makeKey(projectId, mrIid);
      const existing = state.mrReviews[key];
      return {
        mrReviews: {
          ...state.mrReviews,
          [key]: {
            ...(existing ?? createMinimalState(projectId, mrIid)),
            newCommitsCheck: check,
          },
        },
      };
    }),

  clearMRReview: (projectId, mrIid) =>
    set((state) => {
      const key = makeKey(projectId, mrIid);
      const { [key]: _, ...rest } = state.mrReviews;
      return { mrReviews: rest };
    }),

  getMRReviewState: (projectId, mrIid) => {
    const key = makeKey(projectId, mrIid);
    return get().mrReviews[key] ?? null;
  },

  getActiveMRReviews: (projectId) => {
    return Object.values(get().mrReviews).filter(
      (review) => review.projectId === projectId && review.isReviewing,
    );
  },
}));
