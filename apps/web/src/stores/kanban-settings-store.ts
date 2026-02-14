import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// Types matching Electron field names
export type TaskStatusColumn =
  | "planning"
  | "spec_writing"
  | "building"
  | "qa_review"
  | "qa_fixing"
  | "done"
  | "failed"
  | "cancelled";

export interface KanbanColumnPreference {
  width: number;
  isCollapsed: boolean;
  isLocked: boolean;
}

export type KanbanColumnPreferences = Record<
  TaskStatusColumn,
  KanbanColumnPreference
>;

/** Default column width in pixels */
export const DEFAULT_COLUMN_WIDTH = 320;
/** Minimum column width in pixels */
export const MIN_COLUMN_WIDTH = 180;
/** Maximum column width in pixels */
export const MAX_COLUMN_WIDTH = 600;
/** Collapsed column width in pixels */
export const COLLAPSED_COLUMN_WIDTH = 48;

const TASK_STATUS_COLUMNS: TaskStatusColumn[] = [
  "planning",
  "spec_writing",
  "building",
  "qa_review",
  "qa_fixing",
  "done",
  "failed",
  "cancelled",
];

function createDefaultPreferences(): KanbanColumnPreferences {
  const preferences: Partial<KanbanColumnPreferences> = {};
  for (const column of TASK_STATUS_COLUMNS) {
    preferences[column] = {
      width: DEFAULT_COLUMN_WIDTH,
      isCollapsed: false,
      isLocked: false,
    };
  }
  return preferences as KanbanColumnPreferences;
}

function clampWidth(width: number): number {
  return Math.max(MIN_COLUMN_WIDTH, Math.min(MAX_COLUMN_WIDTH, width));
}

interface KanbanSettingsState {
  columnPreferences: KanbanColumnPreferences | null;

  // Actions
  initializePreferences: () => void;
  setColumnWidth: (column: TaskStatusColumn, width: number) => void;
  toggleColumnCollapsed: (column: TaskStatusColumn) => void;
  setColumnCollapsed: (column: TaskStatusColumn, isCollapsed: boolean) => void;
  toggleColumnLocked: (column: TaskStatusColumn) => void;
  setColumnLocked: (column: TaskStatusColumn, isLocked: boolean) => void;
  resetPreferences: () => void;
  getColumnPreferences: (column: TaskStatusColumn) => KanbanColumnPreference;
}

export const useKanbanSettingsStore = create<KanbanSettingsState>()(
  persist(
    (set, get) => ({
      columnPreferences: null,

      initializePreferences: () => {
        const state = get();
        if (!state.columnPreferences) {
          set({ columnPreferences: createDefaultPreferences() });
        }
      },

      setColumnWidth: (column, width) => {
        set((state) => {
          if (!state.columnPreferences) return state;
          if (state.columnPreferences[column].isLocked) return state;
          return {
            columnPreferences: {
              ...state.columnPreferences,
              [column]: {
                ...state.columnPreferences[column],
                width: clampWidth(width),
              },
            },
          };
        });
      },

      toggleColumnCollapsed: (column) => {
        set((state) => {
          if (!state.columnPreferences) return state;
          return {
            columnPreferences: {
              ...state.columnPreferences,
              [column]: {
                ...state.columnPreferences[column],
                isCollapsed: !state.columnPreferences[column].isCollapsed,
              },
            },
          };
        });
      },

      setColumnCollapsed: (column, isCollapsed) => {
        set((state) => {
          if (!state.columnPreferences) return state;
          return {
            columnPreferences: {
              ...state.columnPreferences,
              [column]: {
                ...state.columnPreferences[column],
                isCollapsed,
              },
            },
          };
        });
      },

      toggleColumnLocked: (column) => {
        set((state) => {
          if (!state.columnPreferences) return state;
          return {
            columnPreferences: {
              ...state.columnPreferences,
              [column]: {
                ...state.columnPreferences[column],
                isLocked: !state.columnPreferences[column].isLocked,
              },
            },
          };
        });
      },

      setColumnLocked: (column, isLocked) => {
        set((state) => {
          if (!state.columnPreferences) return state;
          return {
            columnPreferences: {
              ...state.columnPreferences,
              [column]: {
                ...state.columnPreferences[column],
                isLocked,
              },
            },
          };
        });
      },

      resetPreferences: () => {
        set({ columnPreferences: createDefaultPreferences() });
      },

      getColumnPreferences: (column) => {
        const state = get();
        if (!state.columnPreferences) {
          return {
            width: DEFAULT_COLUMN_WIDTH,
            isCollapsed: false,
            isLocked: false,
          };
        }
        return state.columnPreferences[column];
      },
    }),
    {
      name: "kanban-column-prefs",
      storage: createJSONStorage(() => localStorage),
      skipHydration: true,
    },
  ),
);
