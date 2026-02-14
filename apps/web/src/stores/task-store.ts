import { create } from "zustand";
import type { Task, TaskStatus } from "@auto-claude/types";
import { apiClient } from "@/lib/data";

interface TaskState {
  tasks: Task[];
  isLoading: boolean;
  error: string | null;

  // Actions
  setTasks: (tasks: Task[]) => void;
  clearTasks: () => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  isLoading: false,
  error: null,

  setTasks: (tasks) => set({ tasks }),

  clearTasks: () => set({ tasks: [] }),

  updateTask: (taskId, updates) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === taskId ? { ...t, ...updates } : t
      ),
    })),
}));

export async function loadTasks(projectId: string) {
  useTaskStore.setState({ isLoading: true, error: null });
  try {
    const result = await apiClient.getTasks(projectId);
    useTaskStore.setState({
      tasks: result.tasks as Task[],
      isLoading: false,
    });
  } catch (error) {
    useTaskStore.setState({
      isLoading: false,
      error: error instanceof Error ? error.message : "Failed to load tasks",
    });
  }
}

export async function updateTaskStatus(
  projectId: string,
  taskId: string,
  status: TaskStatus
) {
  try {
    await apiClient.updateTaskStatus(projectId, taskId, status);
    useTaskStore.getState().updateTask(taskId, { status });
  } catch (error) {
    console.error("Failed to update task status:", error);
  }
}
