import { create } from "zustand";
import type {
  Task,
  TaskStatus,
  TaskOrderState,
  ImplementationPlan,
  ExecutionProgress,
  ReviewReason,
} from "@auto-claude/types";
import { apiClient } from "@/lib/data";

/** Default max parallel tasks when no project setting is configured */
export const DEFAULT_MAX_PARALLEL_TASKS = 3;

const VALID_TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  backlog: ["queue"],
  queue: ["in_progress", "backlog"],
  in_progress: ["ai_review", "human_review", "error", "backlog"],
  ai_review: ["in_progress", "done", "human_review", "error"],
  human_review: ["in_progress", "done", "backlog"],
  done: ["backlog"],
  pr_created: ["done"],
  error: ["in_progress", "human_review", "backlog"],
};

// localStorage key prefix for task order persistence
const TASK_ORDER_KEY_PREFIX = "task-order-state";

function getTaskOrderKey(projectId: string): string {
  return `${TASK_ORDER_KEY_PREFIX}-${projectId}`;
}

function createEmptyTaskOrder(): TaskOrderState {
  return {
    backlog: [],
    queue: [],
    in_progress: [],
    ai_review: [],
    human_review: [],
    done: [],
    pr_created: [],
    error: [],
  };
}

/**
 * Find task index by id or specId.
 */
function findTaskIndex(tasks: Task[], taskId: string): number {
  return tasks.findIndex((t) => t.id === taskId || t.specId === taskId);
}

/**
 * Task status change listeners for queue auto-promotion.
 * Stored outside the store to avoid triggering re-renders.
 */
const taskStatusChangeListeners = new Set<
  (taskId: string, oldStatus: TaskStatus | undefined, newStatus: TaskStatus) => void
>();

function notifyTaskStatusChange(
  taskId: string,
  oldStatus: TaskStatus | undefined,
  newStatus: TaskStatus,
): void {
  for (const listener of taskStatusChangeListeners) {
    try {
      listener(taskId, oldStatus, newStatus);
    } catch (error) {
      console.error("[TaskStore] Error in task status change listener:", error);
    }
  }
}

interface TaskState {
  tasks: Task[];
  selectedTaskId: string | null;
  isLoading: boolean;
  error: string | null;
  taskOrder: TaskOrderState | null;

  // Actions
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  updateTaskStatus: (
    taskId: string,
    status: TaskStatus,
    reviewReason?: ReviewReason,
  ) => void;
  updateTaskFromPlan: (taskId: string, plan: ImplementationPlan) => void;
  updateExecutionProgress: (
    taskId: string,
    progress: Partial<ExecutionProgress>,
  ) => void;
  appendLog: (taskId: string, log: string) => void;
  batchAppendLogs: (taskId: string, logs: string[]) => void;
  selectTask: (taskId: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearTasks: () => void;

  // Task order actions for kanban drag-and-drop reordering
  setTaskOrder: (order: TaskOrderState) => void;
  reorderTasksInColumn: (
    status: TaskStatus,
    activeId: string,
    overId: string,
  ) => void;
  moveTaskToColumnTop: (
    taskId: string,
    targetStatus: TaskStatus,
    sourceStatus?: TaskStatus,
  ) => void;
  loadTaskOrder: (projectId: string) => void;
  saveTaskOrder: (projectId: string) => boolean;
  clearTaskOrder: (projectId: string) => void;

  // Task status change listeners
  registerTaskStatusChangeListener: (
    listener: (
      taskId: string,
      oldStatus: TaskStatus | undefined,
      newStatus: TaskStatus,
    ) => void,
  ) => () => void;

  // Selectors
  getSelectedTask: () => Task | undefined;
  getTasksByStatus: (status: TaskStatus) => Task[];
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  selectedTaskId: null,
  isLoading: false,
  error: null,
  taskOrder: null,

  setTasks: (tasks) => set({ tasks }),

  addTask: (task) =>
    set((state) => ({ tasks: [...state.tasks, task] })),

  updateTask: (taskId, updates) =>
    set((state) => {
      const index = findTaskIndex(state.tasks, taskId);
      if (index === -1) return state;

      const oldTask = state.tasks[index];
      const newTask = { ...oldTask, ...updates };

      // Notify listeners if status changed
      if (updates.status && updates.status !== oldTask.status) {
        notifyTaskStatusChange(taskId, oldTask.status, updates.status);
      }

      const newTasks = [...state.tasks];
      newTasks[index] = newTask;
      return { tasks: newTasks };
    }),

  updateTaskStatus: (taskId, status, reviewReason) => {
    const state = get();
    const index = findTaskIndex(state.tasks, taskId);
    if (index === -1) return;

    const oldTask = state.tasks[index];
    const oldStatus = oldTask.status;

    // Validate transition
    if (!VALID_TRANSITIONS[oldStatus]?.includes(status)) {
      console.warn(
        `[TaskStore] Invalid transition: ${oldStatus} -> ${status}`,
      );
      return;
    }

    const updates: Partial<Task> = { status };
    if (reviewReason && status === "human_review") {
      updates.reviewReason = reviewReason;
    }
    if (status !== "human_review") {
      updates.reviewReason = undefined;
    }

    get().updateTask(taskId, updates);
  },

  updateTaskFromPlan: (taskId, plan) => {
    const state = get();
    const index = findTaskIndex(state.tasks, taskId);
    if (index === -1) return;

    const subtasks =
      plan.phases?.flatMap((phase) =>
        phase.subtasks.map((s) => ({
          id: s.id,
          title: s.description,
          description: s.description,
          status: s.status,
          files: [],
          verification: s.verification
            ? {
                type: s.verification.type as "command" | "browser",
                run: s.verification.run,
                scenario: s.verification.scenario,
              }
            : undefined,
        })),
      ) ?? [];

    get().updateTask(taskId, { subtasks });
  },

  updateExecutionProgress: (taskId, progress) =>
    set((state) => {
      const index = findTaskIndex(state.tasks, taskId);
      if (index === -1) return state;

      const task = state.tasks[index];
      const currentProgress = task.executionProgress ?? {
        phase: "idle" as const,
        phaseProgress: 0,
        overallProgress: 0,
      };

      // Sequence number check: reject stale updates
      if (
        progress.sequenceNumber !== undefined &&
        currentProgress.sequenceNumber !== undefined &&
        progress.sequenceNumber < currentProgress.sequenceNumber
      ) {
        return state;
      }

      const newTasks = [...state.tasks];
      newTasks[index] = {
        ...task,
        executionProgress: { ...currentProgress, ...progress },
      };
      return { tasks: newTasks };
    }),

  appendLog: (taskId, log) =>
    set((state) => {
      const index = findTaskIndex(state.tasks, taskId);
      if (index === -1) return state;

      const task = state.tasks[index];
      const newTasks = [...state.tasks];
      newTasks[index] = { ...task, logs: [...task.logs, log] };
      return { tasks: newTasks };
    }),

  batchAppendLogs: (taskId, logs) =>
    set((state) => {
      const index = findTaskIndex(state.tasks, taskId);
      if (index === -1) return state;

      const task = state.tasks[index];
      const newTasks = [...state.tasks];
      newTasks[index] = { ...task, logs: [...task.logs, ...logs] };
      return { tasks: newTasks };
    }),

  selectTask: (taskId) => set({ selectedTaskId: taskId }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  clearTasks: () => set({ tasks: [], selectedTaskId: null }),

  // Task order actions
  setTaskOrder: (order) => set({ taskOrder: order }),

  reorderTasksInColumn: (status, activeId, overId) =>
    set((state) => {
      if (!state.taskOrder) return state;
      const column = [...(state.taskOrder[status] ?? [])];
      const activeIndex = column.indexOf(activeId);
      const overIndex = column.indexOf(overId);
      if (activeIndex === -1 || overIndex === -1) return state;

      // Swap positions
      column.splice(activeIndex, 1);
      column.splice(overIndex, 0, activeId);

      return {
        taskOrder: { ...state.taskOrder, [status]: column },
      };
    }),

  moveTaskToColumnTop: (taskId, targetStatus, sourceStatus) =>
    set((state) => {
      if (!state.taskOrder) return state;
      const newOrder = { ...state.taskOrder };

      // Remove from source column
      if (sourceStatus) {
        newOrder[sourceStatus] = (newOrder[sourceStatus] ?? []).filter(
          (id) => id !== taskId,
        );
      }

      // Add to top of target column
      newOrder[targetStatus] = [
        taskId,
        ...(newOrder[targetStatus] ?? []).filter((id) => id !== taskId),
      ];

      return { taskOrder: newOrder };
    }),

  loadTaskOrder: (projectId) => {
    try {
      const raw = localStorage.getItem(getTaskOrderKey(projectId));
      if (raw) {
        const order = JSON.parse(raw) as TaskOrderState;
        set({ taskOrder: order });
      } else {
        set({ taskOrder: createEmptyTaskOrder() });
      }
    } catch {
      set({ taskOrder: createEmptyTaskOrder() });
    }
  },

  saveTaskOrder: (projectId) => {
    const { taskOrder } = get();
    if (!taskOrder) return false;
    try {
      localStorage.setItem(getTaskOrderKey(projectId), JSON.stringify(taskOrder));
      return true;
    } catch {
      return false;
    }
  },

  clearTaskOrder: (projectId) => {
    try {
      localStorage.removeItem(getTaskOrderKey(projectId));
    } catch {
      // Ignore
    }
    set({ taskOrder: createEmptyTaskOrder() });
  },

  registerTaskStatusChangeListener: (listener) => {
    taskStatusChangeListeners.add(listener);
    return () => {
      taskStatusChangeListeners.delete(listener);
    };
  },

  getSelectedTask: () => {
    const state = get();
    return state.tasks.find(
      (t) =>
        t.id === state.selectedTaskId || t.specId === state.selectedTaskId,
    );
  },

  getTasksByStatus: (status) => {
    return get().tasks.filter((t) => t.status === status);
  },
}));

/** Load tasks for a project from API */
export async function loadTasks(projectId: string) {
  useTaskStore.setState({ isLoading: true, error: null });
  try {
    const result = await apiClient.getTasks(projectId);
    useTaskStore.setState({
      tasks: result.tasks as Task[],
      isLoading: false,
    });

    // Load task order for kanban
    useTaskStore.getState().loadTaskOrder(projectId);
  } catch (err) {
    // Network errors (backend not running) and timeouts → silent empty state.
    const isNetworkError =
      err instanceof TypeError ||
      (err instanceof Error && err.name === "AbortError");
    useTaskStore.setState({
      tasks: [],
      isLoading: false,
      error: isNetworkError
        ? null
        : err instanceof Error
          ? err.message
          : "Failed to load tasks",
    });
  }
}

/** Update task status via API with validation */
export async function updateTaskStatusAPI(
  projectId: string,
  taskId: string,
  status: TaskStatus,
  reviewReason?: ReviewReason,
) {
  const currentTask = useTaskStore
    .getState()
    .tasks.find((t) => t.id === taskId || t.specId === taskId);
  if (
    currentTask &&
    !VALID_TRANSITIONS[currentTask.status]?.includes(status)
  ) {
    console.warn(
      `[TaskStore] Invalid transition: ${currentTask.status} -> ${status}`,
    );
    return;
  }

  // Optimistic update
  useTaskStore.getState().updateTaskStatus(taskId, status, reviewReason);

  try {
    await apiClient.updateTaskStatus(projectId, taskId, status);
  } catch (error) {
    // Revert on failure
    if (currentTask) {
      useTaskStore
        .getState()
        .updateTask(taskId, { status: currentTask.status });
    }
    console.error("[TaskStore] Failed to update task status:", error);
  }
}

/** Delete a task via API */
export async function deleteTask(projectId: string, taskId: string) {
  try {
    await apiClient.deleteTask(projectId, taskId);
    useTaskStore.setState((state) => ({
      tasks: state.tasks.filter((t) => t.id !== taskId && t.specId !== taskId),
      selectedTaskId:
        state.selectedTaskId === taskId ? null : state.selectedTaskId,
    }));
  } catch (error) {
    console.error("[TaskStore] Failed to delete task:", error);
  }
}

/** Start a task via API */
export async function startTask(
  projectId: string,
  taskId: string,
  options?: Record<string, unknown>,
) {
  try {
    await apiClient.startTask(projectId, taskId, options);
  } catch (error) {
    console.error("[TaskStore] Failed to start task:", error);
    throw error;
  }
}

/** Stop a task via API */
export async function stopTask(projectId: string, taskId: string) {
  try {
    await apiClient.stopTask(projectId, taskId);
  } catch (error) {
    console.error("[TaskStore] Failed to stop task:", error);
    throw error;
  }
}
