"use client";

import { useMemo, useState, useCallback } from "react";
import {
  Plus,
  Inbox,
  Loader2,
  Eye,
  CheckCircle2,
  RefreshCw,
  GitPullRequest,
  AlertCircle,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { Task, TaskStatus } from "@auto-claude/types";
import { useTaskStore, loadTasks } from "@/stores/task-store";
import { useProjectStore } from "@/stores/project-store";
import { useUIStore } from "@/stores/ui-store";
import { TaskCard } from "./TaskCard";
import { TaskDetailModal } from "./TaskDetailModal";

const TASK_STATUS_COLUMNS: TaskStatus[] = [
  "backlog",
  "queue",
  "in_progress",
  "ai_review",
  "human_review",
  "done",
];

const COLUMN_CONFIG: Record<
  string,
  { label: string; icon: React.ElementType; color: string }
> = {
  backlog: { label: "Backlog", icon: Inbox, color: "text-muted-foreground" },
  queue: { label: "Queue", icon: Loader2, color: "text-blue-500" },
  in_progress: { label: "In Progress", icon: Loader2, color: "text-yellow-500" },
  ai_review: { label: "AI Review", icon: Eye, color: "text-purple-500" },
  human_review: { label: "Human Review", icon: Eye, color: "text-orange-500" },
  done: { label: "Done", icon: CheckCircle2, color: "text-green-500" },
  pr_created: { label: "PR Created", icon: GitPullRequest, color: "text-green-600" },
  error: { label: "Error", icon: AlertCircle, color: "text-red-500" },
};

export function KanbanBoard() {
  const tasks = useTaskStore((s) => s.tasks);
  const isLoading = useTaskStore((s) => s.isLoading);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);
  const setNewTaskDialogOpen = useUIStore((s) => s.setNewTaskDialogOpen);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const currentProjectId = activeProjectId || selectedProjectId;

  // Group tasks by status
  const tasksByStatus = useMemo(() => {
    const grouped: Record<string, Task[]> = {};
    for (const status of TASK_STATUS_COLUMNS) {
      grouped[status] = [];
    }
    for (const task of tasks) {
      // Map pr_created to done, error to human_review for display
      const displayStatus =
        task.status === "pr_created"
          ? "done"
          : task.status === "error"
            ? "human_review"
            : task.status;
      if (grouped[displayStatus]) {
        grouped[displayStatus].push(task);
      }
    }
    return grouped;
  }, [tasks]);

  const handleRefresh = useCallback(async () => {
    if (!currentProjectId) return;
    setIsRefreshing(true);
    try {
      await loadTasks(currentProjectId);
    } finally {
      setIsRefreshing(false);
    }
  }, [currentProjectId]);

  if (isLoading && tasks.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <h1 className="text-lg font-semibold">Tasks</h1>
        <div className="flex items-center gap-2">
          <button
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw
              className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")}
            />
            Refresh
          </button>
          <button
            className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors"
            onClick={() => setNewTaskDialogOpen(true)}
          >
            <Plus className="h-3.5 w-3.5" />
            New Task
          </button>
        </div>
      </div>

      {/* Columns */}
      <div className="flex flex-1 overflow-x-auto p-4 gap-4">
        {TASK_STATUS_COLUMNS.map((status) => {
          const config = COLUMN_CONFIG[status];
          const columnTasks = tasksByStatus[status] || [];
          const Icon = config.icon;

          return (
            <div
              key={status}
              className="flex min-w-[280px] max-w-[320px] flex-1 flex-col rounded-lg bg-card/50 border border-border"
            >
              {/* Column header */}
              <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border">
                <Icon className={cn("h-4 w-4", config.color)} />
                <span className="text-sm font-medium">{config.label}</span>
                <span className="ml-auto rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
                  {columnTasks.length}
                </span>
              </div>

              {/* Tasks */}
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {columnTasks.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                    <p className="text-xs">No tasks</p>
                  </div>
                ) : (
                  columnTasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onClick={() => setSelectedTask(task)}
                    />
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Task Detail Modal */}
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
        />
      )}
    </div>
  );
}
