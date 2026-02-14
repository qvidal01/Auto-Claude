"use client";

import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui";
import { useAgentProgress } from "@/hooks/useAgentProgress";
import { PhaseProgressIndicator } from "@/components/common/PhaseProgressIndicator";
import type { Task } from "@auto-claude/types";

interface TaskProgressProps {
  task: Task;
}

export function TaskProgress({ task }: TaskProgressProps) {
  const { t } = useTranslation(["kanban"]);
  const agentProgress = useAgentProgress(
    task.status === "in_progress" ? task.id : null,
  );

  const progress = task.executionProgress;
  const isRunning = task.status === "in_progress";

  return (
    <div className="space-y-4">
      {/* Phase progress indicator */}
      <PhaseProgressIndicator
        phase={progress?.phase}
        subtasks={task.subtasks}
        phaseProgress={progress?.phaseProgress}
        isRunning={isRunning}
      />

      {/* Overall progress */}
      {progress && (
        <div className="rounded-lg border border-border p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground capitalize">
              {t("kanban:detail.phase", { phase: progress.phase })}
            </span>
            <span className="text-sm font-medium">
              {progress.overallProgress}%
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-secondary">
            <div
              className={cn(
                "h-2 rounded-full bg-primary transition-all duration-500 ease-out",
              )}
              style={{ width: `${progress.overallProgress}%` }}
            />
          </div>
          {progress.message && (
            <p className="mt-2 text-xs text-muted-foreground">
              {progress.message}
            </p>
          )}
          {progress.currentSubtask && (
            <p className="mt-1 text-xs text-muted-foreground">
              {t("kanban:detail.currentSubtask", "Current: {{subtask}}", {
                subtask: progress.currentSubtask,
              })}
            </p>
          )}
        </div>
      )}

      {/* Agent progress status */}
      {agentProgress.isRunning && agentProgress.message && (
        <div className="rounded-md border border-border bg-muted/30 p-3">
          <p className="text-xs text-muted-foreground">
            {agentProgress.message}
          </p>
        </div>
      )}

      {agentProgress.error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3">
          <p className="text-xs text-destructive">{agentProgress.error}</p>
        </div>
      )}
    </div>
  );
}
