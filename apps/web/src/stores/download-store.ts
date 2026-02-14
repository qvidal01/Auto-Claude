import { create } from "zustand";

export interface DownloadProgress {
  modelName: string;
  status: "starting" | "downloading" | "completed" | "failed";
  percentage: number;
  speed?: string;
  timeRemaining?: string;
  error?: string;
}

interface DownloadState {
  // Map of modelName -> progress
  downloads: Record<string, DownloadProgress>;

  // Actions
  startDownload: (modelName: string) => void;
  updateProgress: (
    modelName: string,
    progress: Partial<DownloadProgress>,
  ) => void;
  completeDownload: (modelName: string) => void;
  failDownload: (modelName: string, error: string) => void;
  clearDownload: (modelName: string) => void;

  // Selectors
  hasActiveDownloads: () => boolean;
  getActiveDownloads: () => DownloadProgress[];
}

export const useDownloadStore = create<DownloadState>((set, get) => ({
  downloads: {},

  startDownload: (modelName: string) =>
    set((state) => ({
      downloads: {
        ...state.downloads,
        [modelName]: {
          modelName,
          status: "starting",
          percentage: 0,
        },
      },
    })),

  updateProgress: (modelName: string, progress: Partial<DownloadProgress>) =>
    set((state) => {
      const existing = state.downloads[modelName];
      if (!existing) return state;

      return {
        downloads: {
          ...state.downloads,
          [modelName]: {
            ...existing,
            ...progress,
            status:
              progress.percentage !== undefined && progress.percentage > 0
                ? "downloading"
                : existing.status,
          },
        },
      };
    }),

  completeDownload: (modelName: string) =>
    set((state) => {
      const existing = state.downloads[modelName];
      if (!existing) return state;

      return {
        downloads: {
          ...state.downloads,
          [modelName]: {
            ...existing,
            status: "completed",
            percentage: 100,
          },
        },
      };
    }),

  failDownload: (modelName: string, error: string) =>
    set((state) => {
      const existing = state.downloads[modelName];
      if (!existing) return state;

      return {
        downloads: {
          ...state.downloads,
          [modelName]: {
            ...existing,
            status: "failed",
            error,
          },
        },
      };
    }),

  clearDownload: (modelName: string) =>
    set((state) => {
      const { [modelName]: _, ...rest } = state.downloads;
      return { downloads: rest };
    }),

  hasActiveDownloads: () => {
    const downloads = get().downloads;
    return Object.values(downloads).some(
      (d) => d.status === "starting" || d.status === "downloading",
    );
  },

  getActiveDownloads: () => {
    const downloads = get().downloads;
    return Object.values(downloads).filter(
      (d) => d.status === "starting" || d.status === "downloading",
    );
  },
}));
