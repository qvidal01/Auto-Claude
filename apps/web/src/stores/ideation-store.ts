import { create } from "zustand";

// Types matching Electron field names
export type IdeationStatus =
  | "new"
  | "reviewed"
  | "converted"
  | "dismissed"
  | "archived";

export type IdeationType =
  | "code_improvements"
  | "ui_ux_improvements"
  | "documentation_gaps"
  | "security_hardening"
  | "performance_optimizations"
  | "code_quality";

export type IdeationTypeState =
  | "pending"
  | "generating"
  | "completed"
  | "failed";

export interface Idea {
  id: string;
  type: IdeationType;
  title: string;
  description: string;
  priority: number;
  effort: string;
  impact: string;
  status: IdeationStatus;
  taskId?: string;
  createdAt: Date;
}

export interface IdeationSession {
  id: string;
  projectId: string;
  ideas: Idea[];
  createdAt: Date;
  updatedAt: Date;
}

export interface IdeationGenerationStatus {
  phase: "idle" | "analyzing" | "generating" | "complete" | "error";
  progress: number;
  message: string;
}

export interface IdeationConfig {
  enabledTypes: IdeationType[];
  includeRoadmapContext: boolean;
  includeKanbanContext: boolean;
  maxIdeasPerType: number;
}

const DEFAULT_CONFIG: IdeationConfig = {
  enabledTypes: [
    "code_improvements",
    "ui_ux_improvements",
    "documentation_gaps",
    "security_hardening",
    "performance_optimizations",
    "code_quality",
  ],
  includeRoadmapContext: true,
  includeKanbanContext: true,
  maxIdeasPerType: 5,
};

const initialGenerationStatus: IdeationGenerationStatus = {
  phase: "idle",
  progress: 0,
  message: "",
};

const initialTypeStates: Record<IdeationType, IdeationTypeState> = {
  code_improvements: "pending",
  ui_ux_improvements: "pending",
  documentation_gaps: "pending",
  security_hardening: "pending",
  performance_optimizations: "pending",
  code_quality: "pending",
};

interface IdeationState {
  // Data
  currentProjectId: string | null;
  session: IdeationSession | null;
  generationStatus: IdeationGenerationStatus;
  config: IdeationConfig;
  logs: string[];
  typeStates: Record<IdeationType, IdeationTypeState>;
  selectedIds: Set<string>;
  isGenerating: boolean;

  // Actions
  setCurrentProjectId: (projectId: string | null) => void;
  setSession: (session: IdeationSession | null) => void;
  setIsGenerating: (isGenerating: boolean) => void;
  setGenerationStatus: (status: IdeationGenerationStatus) => void;
  setConfig: (config: Partial<IdeationConfig>) => void;
  updateIdeaStatus: (ideaId: string, status: IdeationStatus) => void;
  setIdeaTaskId: (ideaId: string, taskId: string) => void;
  dismissIdea: (ideaId: string) => void;
  dismissAllIdeas: () => void;
  archiveIdea: (ideaId: string) => void;
  deleteIdea: (ideaId: string) => void;
  deleteMultipleIdeas: (ideaIds: string[]) => void;
  clearSession: () => void;
  addLog: (log: string) => void;
  clearLogs: () => void;
  toggleSelectIdea: (ideaId: string) => void;
  selectAllIdeas: (ideaIds: string[]) => void;
  clearSelection: () => void;
  initializeTypeStates: (types: IdeationType[]) => void;
  setTypeState: (type: IdeationType, state: IdeationTypeState) => void;
  addIdeasForType: (ideationType: string, ideas: Idea[]) => void;
  resetGeneratingTypes: (toState: IdeationTypeState) => void;
}

const MAX_LOG_ENTRIES = 500;

export const useIdeationStore = create<IdeationState>((set) => ({
  currentProjectId: null,
  session: null,
  generationStatus: initialGenerationStatus,
  config: { ...DEFAULT_CONFIG },
  logs: [],
  typeStates: { ...initialTypeStates },
  selectedIds: new Set<string>(),
  isGenerating: false,

  setCurrentProjectId: (projectId) =>
    set((state) => {
      if (state.currentProjectId !== projectId) {
        return {
          currentProjectId: projectId,
          session: null,
          generationStatus: initialGenerationStatus,
          logs: [],
          typeStates: { ...initialTypeStates },
          selectedIds: new Set<string>(),
          isGenerating: false,
        };
      }
      return { currentProjectId: projectId };
    }),

  setSession: (session) => set({ session }),
  setIsGenerating: (isGenerating) => set({ isGenerating }),
  setGenerationStatus: (status) => set({ generationStatus: status }),

  setConfig: (newConfig) =>
    set((state) => ({
      config: { ...state.config, ...newConfig },
    })),

  updateIdeaStatus: (ideaId, status) =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          ideas: state.session.ideas.map((idea) =>
            idea.id === ideaId ? { ...idea, status } : idea,
          ),
          updatedAt: new Date(),
        },
      };
    }),

  setIdeaTaskId: (ideaId, taskId) =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          ideas: state.session.ideas.map((idea) =>
            idea.id === ideaId
              ? {
                  ...idea,
                  taskId,
                  status: "archived" as IdeationStatus,
                }
              : idea,
          ),
          updatedAt: new Date(),
        },
      };
    }),

  dismissIdea: (ideaId) =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          ideas: state.session.ideas.map((idea) =>
            idea.id === ideaId
              ? { ...idea, status: "dismissed" as IdeationStatus }
              : idea,
          ),
          updatedAt: new Date(),
        },
      };
    }),

  dismissAllIdeas: () =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          ideas: state.session.ideas.map((idea) =>
            idea.status !== "dismissed" &&
            idea.status !== "converted" &&
            idea.status !== "archived"
              ? { ...idea, status: "dismissed" as IdeationStatus }
              : idea,
          ),
          updatedAt: new Date(),
        },
      };
    }),

  archiveIdea: (ideaId) =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          ideas: state.session.ideas.map((idea) =>
            idea.id === ideaId
              ? { ...idea, status: "archived" as IdeationStatus }
              : idea,
          ),
          updatedAt: new Date(),
        },
      };
    }),

  deleteIdea: (ideaId) =>
    set((state) => {
      if (!state.session) return state;
      return {
        session: {
          ...state.session,
          ideas: state.session.ideas.filter((idea) => idea.id !== ideaId),
          updatedAt: new Date(),
        },
        selectedIds: (() => {
          const next = new Set(state.selectedIds);
          next.delete(ideaId);
          return next;
        })(),
      };
    }),

  deleteMultipleIdeas: (ideaIds) =>
    set((state) => {
      if (!state.session) return state;
      const idsToDelete = new Set(ideaIds);
      return {
        session: {
          ...state.session,
          ideas: state.session.ideas.filter(
            (idea) => !idsToDelete.has(idea.id),
          ),
          updatedAt: new Date(),
        },
        selectedIds: new Set<string>(),
      };
    }),

  clearSession: () =>
    set({
      session: null,
      generationStatus: initialGenerationStatus,
      logs: [],
      typeStates: { ...initialTypeStates },
      selectedIds: new Set<string>(),
      isGenerating: false,
    }),

  addLog: (log) =>
    set((state) => {
      const newLogs = [...state.logs, log];
      if (newLogs.length > MAX_LOG_ENTRIES) {
        newLogs.splice(0, newLogs.length - MAX_LOG_ENTRIES);
      }
      return { logs: newLogs };
    }),

  clearLogs: () => set({ logs: [] }),

  toggleSelectIdea: (ideaId) =>
    set((state) => {
      const next = new Set(state.selectedIds);
      if (next.has(ideaId)) {
        next.delete(ideaId);
      } else {
        next.add(ideaId);
      }
      return { selectedIds: next };
    }),

  selectAllIdeas: (ideaIds) => set({ selectedIds: new Set(ideaIds) }),

  clearSelection: () => set({ selectedIds: new Set<string>() }),

  initializeTypeStates: (types) =>
    set(() => {
      const states = { ...initialTypeStates };
      for (const type of types) {
        states[type] = "generating";
      }
      return { typeStates: states };
    }),

  setTypeState: (type, state) =>
    set((s) => ({
      typeStates: { ...s.typeStates, [type]: state },
    })),

  addIdeasForType: (ideationType, ideas) =>
    set((state) => {
      if (!state.session) {
        return {
          session: {
            id: `session-${Date.now()}`,
            projectId: state.currentProjectId || "",
            ideas,
            createdAt: new Date(),
            updatedAt: new Date(),
          },
        };
      }
      return {
        session: {
          ...state.session,
          ideas: [...state.session.ideas, ...ideas],
          updatedAt: new Date(),
        },
      };
    }),

  resetGeneratingTypes: (toState) =>
    set((state) => {
      const newStates = { ...state.typeStates };
      for (const key of Object.keys(newStates) as IdeationType[]) {
        if (newStates[key] === "generating") {
          newStates[key] = toState;
        }
      }
      return { typeStates: newStates };
    }),
}));
