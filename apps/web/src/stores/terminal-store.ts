import { create } from "zustand";

export type TerminalStatus = "idle" | "running" | "claude-active" | "exited";

export interface Terminal {
  id: string;
  title: string;
  status: TerminalStatus;
  cwd: string;
  createdAt: Date;
  isClaudeMode: boolean;
  claudeSessionId?: string;
  isRestored?: boolean;
  associatedTaskId?: string;
  projectPath?: string;
  isClaudeBusy?: boolean;
  pendingClaudeResume?: boolean;
  displayOrder?: number;
  claudeNamedOnce?: boolean;
}

interface TerminalLayout {
  id: string;
  row: number;
  col: number;
  rowSpan: number;
  colSpan: number;
}

/**
 * Module-level Map for terminal ID -> output write callback mappings.
 * Stored outside Zustand because callbacks are functions that shouldn't be serialized.
 */
const xtermCallbacks = new Map<string, (data: string) => void>();

/** Register an xterm write callback for a terminal */
export function registerOutputCallback(
  terminalId: string,
  callback: (data: string) => void,
): void {
  xtermCallbacks.set(terminalId, callback);
}

/** Unregister an xterm write callback for a terminal */
export function unregisterOutputCallback(terminalId: string): void {
  xtermCallbacks.delete(terminalId);
}

/** Write terminal output to the appropriate destination */
export function writeToTerminal(terminalId: string, data: string): void {
  const callback = xtermCallbacks.get(terminalId);
  if (callback) {
    try {
      callback(data);
    } catch {
      // Silently handle write errors
    }
  }
}

interface TerminalState {
  terminals: Terminal[];
  layouts: TerminalLayout[];
  activeTerminalId: string | null;
  maxTerminals: number;
  hasRestoredSessions: boolean;

  // Actions
  addTerminal: (cwd?: string, projectPath?: string) => Terminal | null;
  addExternalTerminal: (
    id: string,
    title: string,
    cwd?: string,
    projectPath?: string,
  ) => Terminal | null;
  removeTerminal: (id: string) => void;
  updateTerminal: (id: string, updates: Partial<Terminal>) => void;
  setActiveTerminal: (id: string | null) => void;
  setTerminalStatus: (id: string, status: TerminalStatus) => void;
  setClaudeMode: (id: string, isClaudeMode: boolean) => void;
  setClaudeSessionId: (id: string, sessionId: string) => void;
  setAssociatedTask: (id: string, taskId: string | undefined) => void;
  setClaudeBusy: (id: string, isBusy: boolean) => void;
  setPendingClaudeResume: (id: string, pending: boolean) => void;
  setClaudeNamedOnce: (id: string, named: boolean) => void;
  clearAllTerminals: () => void;
  setHasRestoredSessions: (value: boolean) => void;
  reorderTerminals: (activeId: string, overId: string) => void;

  // Selectors
  getTerminal: (id: string) => Terminal | undefined;
  getActiveTerminal: () => Terminal | undefined;
  canAddTerminal: (projectPath?: string) => boolean;
  getTerminalsForProject: (projectPath: string) => Terminal[];
}

function getActiveProjectTerminalCount(
  terminals: Terminal[],
  projectPath?: string,
): number {
  return terminals.filter(
    (t) => t.status !== "exited" && t.projectPath === projectPath,
  ).length;
}

export const useTerminalStore = create<TerminalState>((set, get) => ({
  terminals: [],
  layouts: [],
  activeTerminalId: null,
  maxTerminals: 12,
  hasRestoredSessions: false,

  addTerminal: (cwd?: string, projectPath?: string) => {
    const state = get();
    const activeCount = getActiveProjectTerminalCount(
      state.terminals,
      projectPath,
    );
    if (activeCount >= state.maxTerminals) {
      return null;
    }

    const newTerminal: Terminal = {
      id: crypto.randomUUID(),
      title: `Terminal ${state.terminals.length + 1}`,
      status: "idle",
      cwd: cwd || "~",
      createdAt: new Date(),
      isClaudeMode: false,
      projectPath,
      displayOrder: state.terminals.length,
    };

    set((s) => ({
      terminals: [...s.terminals, newTerminal],
      activeTerminalId: newTerminal.id,
    }));

    return newTerminal;
  },

  addExternalTerminal: (
    id: string,
    title: string,
    cwd?: string,
    projectPath?: string,
  ) => {
    const state = get();
    const activeCount = getActiveProjectTerminalCount(
      state.terminals,
      projectPath,
    );
    if (activeCount >= state.maxTerminals) {
      return null;
    }

    const newTerminal: Terminal = {
      id,
      title,
      status: "idle",
      cwd: cwd || "~",
      createdAt: new Date(),
      isClaudeMode: false,
      projectPath,
      displayOrder: state.terminals.length,
    };

    set((s) => ({
      terminals: [...s.terminals, newTerminal],
      activeTerminalId: newTerminal.id,
    }));

    return newTerminal;
  },

  removeTerminal: (id) => {
    set((state) => {
      const filtered = state.terminals.filter((t) => t.id !== id);
      const newActiveId =
        state.activeTerminalId === id
          ? (filtered[filtered.length - 1]?.id ?? null)
          : state.activeTerminalId;
      return { terminals: filtered, activeTerminalId: newActiveId };
    });
    unregisterOutputCallback(id);
  },

  updateTerminal: (id, updates) => {
    set((state) => ({
      terminals: state.terminals.map((t) =>
        t.id === id ? { ...t, ...updates } : t,
      ),
    }));
  },

  setActiveTerminal: (id) => set({ activeTerminalId: id }),

  setTerminalStatus: (id, status) => {
    set((state) => ({
      terminals: state.terminals.map((t) =>
        t.id === id ? { ...t, status } : t,
      ),
    }));
  },

  setClaudeMode: (id, isClaudeMode) => {
    set((state) => ({
      terminals: state.terminals.map((t) =>
        t.id === id ? { ...t, isClaudeMode } : t,
      ),
    }));
  },

  setClaudeSessionId: (id, sessionId) => {
    set((state) => ({
      terminals: state.terminals.map((t) =>
        t.id === id ? { ...t, claudeSessionId: sessionId } : t,
      ),
    }));
  },

  setAssociatedTask: (id, taskId) => {
    set((state) => ({
      terminals: state.terminals.map((t) =>
        t.id === id ? { ...t, associatedTaskId: taskId } : t,
      ),
    }));
  },

  setClaudeBusy: (id, isBusy) => {
    set((state) => ({
      terminals: state.terminals.map((t) =>
        t.id === id ? { ...t, isClaudeBusy: isBusy } : t,
      ),
    }));
  },

  setPendingClaudeResume: (id, pending) => {
    set((state) => ({
      terminals: state.terminals.map((t) =>
        t.id === id ? { ...t, pendingClaudeResume: pending } : t,
      ),
    }));
  },

  setClaudeNamedOnce: (id, named) => {
    set((state) => ({
      terminals: state.terminals.map((t) =>
        t.id === id ? { ...t, claudeNamedOnce: named } : t,
      ),
    }));
  },

  clearAllTerminals: () => {
    xtermCallbacks.clear();
    set({ terminals: [], activeTerminalId: null, hasRestoredSessions: false });
  },

  setHasRestoredSessions: (value) => set({ hasRestoredSessions: value }),

  reorderTerminals: (activeId, overId) => {
    set((state) => {
      const oldIndex = state.terminals.findIndex((t) => t.id === activeId);
      const newIndex = state.terminals.findIndex((t) => t.id === overId);
      if (oldIndex === -1 || newIndex === -1) return state;

      const newTerminals = [...state.terminals];
      const [moved] = newTerminals.splice(oldIndex, 1);
      newTerminals.splice(newIndex, 0, moved);

      return {
        terminals: newTerminals.map((t, i) => ({ ...t, displayOrder: i })),
      };
    });
  },

  getTerminal: (id) => get().terminals.find((t) => t.id === id),
  getActiveTerminal: () =>
    get().terminals.find((t) => t.id === get().activeTerminalId),
  canAddTerminal: (projectPath) =>
    getActiveProjectTerminalCount(get().terminals, projectPath) <
    get().maxTerminals,
  getTerminalsForProject: (projectPath) =>
    get().terminals.filter((t) => t.projectPath === projectPath),
}));
