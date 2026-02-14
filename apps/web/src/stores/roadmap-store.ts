import { create } from "zustand";

// Types matching Electron field names
export type RoadmapFeatureStatus =
  | "under_review"
  | "planned"
  | "in_progress"
  | "done";

export type TaskOutcome = "completed" | "cancelled" | "failed";

export interface FeatureSource {
  provider: "internal" | "github" | "linear" | "gitlab";
  issueId?: string;
  issueUrl?: string;
}

export interface RoadmapFeature {
  id: string;
  title: string;
  description: string;
  status: RoadmapFeatureStatus;
  phaseId: string;
  priority?: number;
  linkedSpecId?: string;
  taskOutcome?: TaskOutcome;
  previousStatus?: RoadmapFeatureStatus;
  source?: FeatureSource;
}

export interface RoadmapPhase {
  id: string;
  title: string;
  description?: string;
  order: number;
}

export interface Roadmap {
  id: string;
  projectId: string;
  title: string;
  description?: string;
  phases: RoadmapPhase[];
  features: RoadmapFeature[];
  createdAt: Date;
  updatedAt: Date;
}

export interface CompetitorAnalysis {
  competitors: Array<{
    name: string;
    strengths: string[];
    weaknesses: string[];
  }>;
  opportunities: string[];
  threats: string[];
}

export interface RoadmapGenerationStatus {
  phase: "idle" | "analyzing" | "generating" | "complete" | "error";
  progress: number;
  message: string;
  startedAt?: Date;
  lastActivityAt?: Date;
}

interface RoadmapState {
  // Data
  roadmap: Roadmap | null;
  competitorAnalysis: CompetitorAnalysis | null;
  generationStatus: RoadmapGenerationStatus;
  currentProjectId: string | null;

  // Actions
  setRoadmap: (roadmap: Roadmap | null) => void;
  setCompetitorAnalysis: (analysis: CompetitorAnalysis | null) => void;
  setGenerationStatus: (status: RoadmapGenerationStatus) => void;
  setCurrentProjectId: (projectId: string | null) => void;
  updateFeatureStatus: (
    featureId: string,
    status: RoadmapFeatureStatus,
  ) => void;
  markFeatureDoneBySpecId: (
    specId: string,
    taskOutcome?: TaskOutcome,
  ) => void;
  updateFeatureLinkedSpec: (featureId: string, specId: string) => void;
  deleteFeature: (featureId: string) => void;
  clearRoadmap: () => void;
  reorderFeatures: (phaseId: string, featureIds: string[]) => void;
  updateFeaturePhase: (featureId: string, newPhaseId: string) => void;
  addFeature: (feature: Omit<RoadmapFeature, "id">) => string;
}

const initialGenerationStatus: RoadmapGenerationStatus = {
  phase: "idle",
  progress: 0,
  message: "",
};

export const useRoadmapStore = create<RoadmapState>((set) => ({
  roadmap: null,
  competitorAnalysis: null,
  generationStatus: initialGenerationStatus,
  currentProjectId: null,

  setRoadmap: (roadmap) => set({ roadmap }),

  setCompetitorAnalysis: (analysis) => set({ competitorAnalysis: analysis }),

  setGenerationStatus: (status) =>
    set((state) => {
      const now = new Date();
      const isStarting =
        state.generationStatus.phase === "idle" && status.phase !== "idle";
      const isStopping =
        status.phase === "idle" ||
        status.phase === "complete" ||
        status.phase === "error";

      return {
        generationStatus: {
          ...status,
          startedAt: isStarting
            ? (status.startedAt ?? now)
            : isStopping
              ? undefined
              : (status.startedAt ?? state.generationStatus.startedAt),
          lastActivityAt: isStopping
            ? undefined
            : (status.lastActivityAt ?? now),
        },
      };
    }),

  setCurrentProjectId: (projectId) => set({ currentProjectId: projectId }),

  updateFeatureStatus: (featureId, status) =>
    set((state) => {
      if (!state.roadmap) return state;
      return {
        roadmap: {
          ...state.roadmap,
          features: state.roadmap.features.map((f) =>
            f.id === featureId
              ? {
                  ...f,
                  status,
                  ...(status !== "done"
                    ? { taskOutcome: undefined, previousStatus: undefined }
                    : {}),
                }
              : f,
          ),
          updatedAt: new Date(),
        },
      };
    }),

  markFeatureDoneBySpecId: (specId, taskOutcome = "completed") =>
    set((state) => {
      if (!state.roadmap) return state;
      return {
        roadmap: {
          ...state.roadmap,
          features: state.roadmap.features.map((f) =>
            f.linkedSpecId === specId
              ? {
                  ...f,
                  status: "done" as RoadmapFeatureStatus,
                  taskOutcome,
                  previousStatus:
                    f.status !== "done" ? f.status : f.previousStatus,
                }
              : f,
          ),
          updatedAt: new Date(),
        },
      };
    }),

  updateFeatureLinkedSpec: (featureId, specId) =>
    set((state) => {
      if (!state.roadmap) return state;
      return {
        roadmap: {
          ...state.roadmap,
          features: state.roadmap.features.map((f) =>
            f.id === featureId
              ? {
                  ...f,
                  linkedSpecId: specId,
                  status: "in_progress" as RoadmapFeatureStatus,
                }
              : f,
          ),
          updatedAt: new Date(),
        },
      };
    }),

  deleteFeature: (featureId) =>
    set((state) => {
      if (!state.roadmap) return state;
      return {
        roadmap: {
          ...state.roadmap,
          features: state.roadmap.features.filter((f) => f.id !== featureId),
          updatedAt: new Date(),
        },
      };
    }),

  clearRoadmap: () =>
    set({
      roadmap: null,
      competitorAnalysis: null,
      generationStatus: initialGenerationStatus,
      currentProjectId: null,
    }),

  reorderFeatures: (phaseId, featureIds) =>
    set((state) => {
      if (!state.roadmap) return state;
      const phaseFeatures = featureIds
        .map((id) => state.roadmap!.features.find((f) => f.id === id))
        .filter(Boolean) as RoadmapFeature[];
      const otherFeatures = state.roadmap.features.filter(
        (f) => f.phaseId !== phaseId,
      );
      return {
        roadmap: {
          ...state.roadmap,
          features: [...otherFeatures, ...phaseFeatures],
          updatedAt: new Date(),
        },
      };
    }),

  updateFeaturePhase: (featureId, newPhaseId) =>
    set((state) => {
      if (!state.roadmap) return state;
      return {
        roadmap: {
          ...state.roadmap,
          features: state.roadmap.features.map((f) =>
            f.id === featureId ? { ...f, phaseId: newPhaseId } : f,
          ),
          updatedAt: new Date(),
        },
      };
    }),

  addFeature: (feature) => {
    const id = crypto.randomUUID();
    set((state) => {
      if (!state.roadmap) return state;
      return {
        roadmap: {
          ...state.roadmap,
          features: [...state.roadmap.features, { ...feature, id }],
          updatedAt: new Date(),
        },
      };
    });
    return id;
  },
}));
