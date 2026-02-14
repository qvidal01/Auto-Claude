import { create } from "zustand";

// Types matching Electron field names
export interface InsightsChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  suggestedTasks?: Array<{
    title: string;
    description: string;
  }>;
  toolsUsed?: InsightsToolUsage[];
}

export interface InsightsSession {
  id: string;
  projectId: string;
  messages: InsightsChatMessage[];
  createdAt: Date;
  updatedAt: Date;
}

export interface InsightsSessionSummary {
  id: string;
  projectId: string;
  title?: string;
  messageCount: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface InsightsChatStatus {
  phase: "idle" | "thinking" | "responding" | "error";
  message: string;
}

export interface InsightsToolUsage {
  name: string;
  input?: string;
  timestamp: Date;
}

interface ToolUsage {
  name: string;
  input?: string;
}

interface InsightsState {
  // Data
  session: InsightsSession | null;
  sessions: InsightsSessionSummary[];
  status: InsightsChatStatus;
  pendingMessage: string;
  streamingContent: string;
  streamingTasks: NonNullable<InsightsChatMessage["suggestedTasks"]>;
  currentTool: ToolUsage | null;
  toolsUsed: InsightsToolUsage[];
  isLoadingSessions: boolean;

  // Actions
  setSession: (session: InsightsSession | null) => void;
  setSessions: (sessions: InsightsSessionSummary[]) => void;
  setStatus: (status: InsightsChatStatus) => void;
  setPendingMessage: (message: string) => void;
  addMessage: (message: InsightsChatMessage) => void;
  updateLastAssistantMessage: (content: string) => void;
  appendStreamingContent: (content: string) => void;
  clearStreamingContent: () => void;
  setCurrentTool: (tool: ToolUsage | null) => void;
  addToolUsage: (tool: ToolUsage) => void;
  clearToolsUsed: () => void;
  addStreamingTasks: (
    tasks: NonNullable<InsightsChatMessage["suggestedTasks"]>,
  ) => void;
  finalizeStreamingMessage: () => void;
  clearSession: () => void;
  setLoadingSessions: (loading: boolean) => void;
}

const initialStatus: InsightsChatStatus = {
  phase: "idle",
  message: "",
};

export const useInsightsStore = create<InsightsState>((set) => ({
  session: null,
  sessions: [],
  status: initialStatus,
  pendingMessage: "",
  streamingContent: "",
  streamingTasks: [],
  currentTool: null,
  toolsUsed: [],
  isLoadingSessions: false,

  setSession: (session) => set({ session }),
  setSessions: (sessions) => set({ sessions }),
  setStatus: (status) => set({ status }),
  setLoadingSessions: (loading) => set({ isLoadingSessions: loading }),
  setPendingMessage: (message) => set({ pendingMessage: message }),

  addMessage: (message) =>
    set((state) => {
      if (!state.session) {
        return {
          session: {
            id: `session-${Date.now()}`,
            projectId: "",
            messages: [message],
            createdAt: new Date(),
            updatedAt: new Date(),
          },
        };
      }
      return {
        session: {
          ...state.session,
          messages: [...state.session.messages, message],
          updatedAt: new Date(),
        },
      };
    }),

  updateLastAssistantMessage: (content) =>
    set((state) => {
      if (!state.session || state.session.messages.length === 0) return state;
      const messages = [...state.session.messages];
      const lastIndex = messages.length - 1;
      if (messages[lastIndex].role === "assistant") {
        messages[lastIndex] = { ...messages[lastIndex], content };
      }
      return {
        session: { ...state.session, messages, updatedAt: new Date() },
      };
    }),

  appendStreamingContent: (content) =>
    set((state) => ({
      streamingContent: state.streamingContent + content,
    })),

  clearStreamingContent: () =>
    set({ streamingContent: "", streamingTasks: [] }),

  setCurrentTool: (tool) => set({ currentTool: tool }),

  addToolUsage: (tool) =>
    set((state) => ({
      toolsUsed: [
        ...state.toolsUsed,
        { name: tool.name, input: tool.input, timestamp: new Date() },
      ],
    })),

  clearToolsUsed: () => set({ toolsUsed: [] }),

  addStreamingTasks: (tasks) =>
    set((state) => ({
      streamingTasks: [...state.streamingTasks, ...tasks],
    })),

  finalizeStreamingMessage: () =>
    set((state) => {
      const content = state.streamingContent;
      const toolsUsed =
        state.toolsUsed.length > 0 ? [...state.toolsUsed] : undefined;
      const suggestedTasks =
        state.streamingTasks.length > 0
          ? [...state.streamingTasks]
          : undefined;

      if (!content && !suggestedTasks && !toolsUsed) {
        return { streamingContent: "", streamingTasks: [], toolsUsed: [] };
      }

      const newMessage: InsightsChatMessage = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content,
        timestamp: new Date(),
        suggestedTasks,
        toolsUsed,
      };

      if (!state.session) {
        return {
          streamingContent: "",
          streamingTasks: [],
          toolsUsed: [],
          session: {
            id: `session-${Date.now()}`,
            projectId: "",
            messages: [newMessage],
            createdAt: new Date(),
            updatedAt: new Date(),
          },
        };
      }

      return {
        streamingContent: "",
        streamingTasks: [],
        toolsUsed: [],
        session: {
          ...state.session,
          messages: [...state.session.messages, newMessage],
          updatedAt: new Date(),
        },
      };
    }),

  clearSession: () =>
    set({
      session: null,
      status: initialStatus,
      pendingMessage: "",
      streamingContent: "",
      streamingTasks: [],
      currentTool: null,
      toolsUsed: [],
    }),
}));
