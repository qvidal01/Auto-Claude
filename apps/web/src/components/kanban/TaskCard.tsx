"use client";

import {
  AlertCircle,
  CheckCircle2,
  Clock,
  GitPullRequest,
  Eye,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { Task } from "@auto-claude/types";

const STATUS_ICONS: Record<string, React.ElementType> = {
  backlog: Clock,
  queue: Clock,
  in_progress: Clock,
  ai_review: Eye,
  human_review: Eye,
  done: CheckCircle2,
  pr_created: GitPullRequest,
  error: AlertCircle,
};

const PRIORITY_COLORS: Record<string, string> = {
  urgent: "border-l-red-500",
  high: "border-l-orange-500",
  medium: "border-l-yellow-500",
  low: "border-l-blue-500",
};

const CATEGORY_LABELS: Record<string, string> = {
  feature: "Feature",
  bug_fix: "Bug Fix",
  refactoring: "Refactor",
  documentation: "Docs",
  security: "Security",
  performance: "Perf",
  ui_ux: "UI/UX",
  infrastructure: "Infra",
  testing: "Testing",
};

interface TaskCardProps {
  task: Task;
  onClick: () => void;
}

export function TaskCard({ task, onClick }: TaskCardProps) {
  const priority = task.metadata?.priority;
  const category = task.metadata?.category;
  const StatusIcon = STATUS_ICONS[task.status] || Clock;

  // Calculate subtask progress
  const totalSubtasks = task.subtasks?.length || 0;
  const completedSubtasks =
    task.subtasks?.filter((s) => s.status === "completed").length || 0;

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-3 cursor-pointer transition-all hover:shadow-md hover:border-border/80",
        "border-l-2",
        priority ? PRIORITY_COLORS[priority] || "border-l-transparent" : "border-l-transparent"
      )}
      onClick={onClick}
    >
      {/* Title */}
      <h3 className="text-sm font-medium leading-tight line-clamp-2">
        {task.title}
      </h3>

      {/* Description preview */}
      {task.description && (
        <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
          {task.description}
        </p>
      )}

      {/* Metadata row */}
      <div className="mt-2 flex items-center gap-2 flex-wrap">
        {category && (
          <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
            {CATEGORY_LABELS[category] || category}
          </span>
        )}

        {task.metadata?.complexity && (
          <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
            {task.metadata.complexity}
          </span>
        )}

        {/* Subtask progress */}
        {totalSubtasks > 0 && (
          <span className="ml-auto flex items-center gap-1 text-[10px] text-muted-foreground">
            <CheckCircle2 className="h-3 w-3" />
            {completedSubtasks}/{totalSubtasks}
          </span>
        )}
      </div>

      {/* Progress bar for execution */}
      {task.executionProgress && task.executionProgress.overallProgress > 0 && (
        <div className="mt-2">
          <div className="h-1 w-full rounded-full bg-secondary">
            <div
              className="h-1 rounded-full bg-primary transition-all"
              style={{
                width: `${task.executionProgress.overallProgress}%`,
              }}
            />
          </div>
          {task.executionProgress.message && (
            <p className="mt-0.5 text-[10px] text-muted-foreground truncate">
              {task.executionProgress.message}
            </p>
          )}
        </div>
      )}

      {/* Review reason badge */}
      {task.status === "human_review" && task.reviewReason && (
        <div className="mt-2">
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-medium",
              task.reviewReason === "completed" &&
                "bg-green-500/10 text-green-600",
              task.reviewReason === "errors" &&
                "bg-red-500/10 text-red-600",
              task.reviewReason === "qa_rejected" &&
                "bg-orange-500/10 text-orange-600",
              task.reviewReason === "plan_review" &&
                "bg-blue-500/10 text-blue-600"
            )}
          >
            {task.reviewReason === "completed" && "Ready for Review"}
            {task.reviewReason === "errors" && "Has Errors"}
            {task.reviewReason === "qa_rejected" && "QA Rejected"}
            {task.reviewReason === "plan_review" && "Plan Review"}
            {task.reviewReason === "stopped" && "Stopped"}
          </span>
        </div>
      )}
    </div>
  );
}
