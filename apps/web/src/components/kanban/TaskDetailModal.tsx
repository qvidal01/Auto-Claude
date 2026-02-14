"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  GitPullRequest,
  ExternalLink,
} from "lucide-react";
import {
  cn,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Separator,
  TooltipProvider,
} from "@auto-claude/ui";
import { TaskHeader } from "@/components/task-detail/TaskHeader";
import { TaskMetadata } from "@/components/task-detail/TaskMetadata";
import { TaskProgress } from "@/components/task-detail/TaskProgress";
import { TaskSubtasks } from "@/components/task-detail/TaskSubtasks";
import { TaskFiles } from "@/components/task-detail/TaskFiles";
import { TaskLogs } from "@/components/task-detail/TaskLogs";
import { TaskActions } from "@/components/task-detail/TaskActions";
import { TaskReview } from "@/components/task-detail/TaskReview";
import { TaskWarnings } from "@/components/task-detail/TaskWarnings";
import type { Task } from "@auto-claude/types";

interface TaskDetailModalProps {
  task: Task;
  onClose: () => void;
  onStart?: (taskId: string) => void;
  onStop?: (taskId: string) => void;
}

export function TaskDetailModal({ task, onClose, onStart, onStop }: TaskDetailModalProps) {
  const { t } = useTranslation(["kanban", "common"]);
  const [isStuck, setIsStuck] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // Escape key handling
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  // Stuck detection: if in_progress but no updates for 60s
  useEffect(() => {
    if (task.status !== "in_progress") {
      setIsStuck(false);
      return;
    }

    const checkStuck = () => {
      const lastUpdate = task.updatedAt ? new Date(task.updatedAt).getTime() : 0;
      const elapsed = Date.now() - lastUpdate;
      setIsStuck(elapsed > 60_000);
    };

    checkStuck();
    const interval = setInterval(checkStuck, 10_000);
    return () => clearInterval(interval);
  }, [task.status, task.updatedAt]);

  const isRunning = task.status === "in_progress";
  const isIncomplete = useMemo(() => {
    if (task.subtasks.length === 0) return false;
    const completed = task.subtasks.filter((s) => s.status === "completed").length;
    return (
      completed > 0 &&
      completed < task.subtasks.length &&
      !isRunning &&
      task.status !== "done"
    );
  }, [task.subtasks, isRunning, task.status]);

  const taskProgress = useMemo(
    () => ({
      completed: task.subtasks.filter((s) => s.status === "completed").length,
      total: task.subtasks.length,
    }),
    [task.subtasks],
  );

  const hasSubtasks = task.subtasks.length > 0;
  const hasLogs = task.logs.length > 0;
  const isReviewable = task.status === "human_review";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-3xl max-h-[85vh] overflow-hidden rounded-xl border border-border bg-card shadow-2xl flex flex-col">
        <TooltipProvider>
          {/* Header */}
          <TaskHeader
            task={task}
            isStuck={isStuck}
            isIncomplete={isIncomplete}
            taskProgress={taskProgress}
            isRunning={isRunning}
            onClose={onClose}
            onEdit={() => setIsEditing(true)}
          />

          <Separator />

          {/* Warnings */}
          <div className="px-4 pt-3">
            <TaskWarnings task={task} isStuck={isStuck} />
          </div>

          {/* Tabbed Content */}
          <Tabs defaultValue="overview" className="flex-1 flex flex-col min-h-0">
            <div className="px-4 pt-2">
              <TabsList>
                <TabsTrigger value="overview">
                  {t("kanban:detail.tabOverview", "Overview")}
                </TabsTrigger>
                {hasSubtasks && (
                  <TabsTrigger value="subtasks">
                    {t("kanban:detail.tabSubtasks", "Subtasks")}
                    <span className="ml-1 text-xs text-muted-foreground">
                      ({taskProgress.completed}/{taskProgress.total})
                    </span>
                  </TabsTrigger>
                )}
                <TabsTrigger value="files">
                  {t("kanban:detail.tabFiles", "Files")}
                </TabsTrigger>
                {hasLogs && (
                  <TabsTrigger value="logs">
                    {t("kanban:detail.tabLogs", "Logs")}
                  </TabsTrigger>
                )}
                {isReviewable && (
                  <TabsTrigger value="review">
                    {t("kanban:detail.tabReview", "Review")}
                  </TabsTrigger>
                )}
              </TabsList>
            </div>

            <div className="flex-1 overflow-y-auto px-4 pb-4">
              {/* Overview Tab */}
              <TabsContent value="overview" className="space-y-6 mt-4">
                {/* Description */}
                {task.description && (
                  <div>
                    <h3 className="text-sm font-medium mb-2">
                      {t("kanban:detail.description")}
                    </h3>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                      {task.description}
                    </p>
                  </div>
                )}

                {/* Progress */}
                {(task.executionProgress || isRunning) && (
                  <div>
                    <h3 className="text-sm font-medium mb-2">
                      {t("kanban:detail.executionProgress")}
                    </h3>
                    <TaskProgress task={task} />
                  </div>
                )}

                {/* Metadata */}
                <div>
                  <h3 className="text-sm font-medium mb-2">
                    {t("kanban:detail.details")}
                  </h3>
                  <TaskMetadata task={task} />
                </div>

                {/* QA Report */}
                {task.qaReport && (
                  <div>
                    <h3 className="text-sm font-medium mb-2">
                      {t("kanban:detail.qaReport")}
                    </h3>
                    <div
                      className={cn(
                        "rounded-lg border p-4",
                        task.qaReport.status === "passed" &&
                          "border-green-500/30 bg-green-500/5",
                        task.qaReport.status === "failed" &&
                          "border-red-500/30 bg-red-500/5",
                        task.qaReport.status === "pending" &&
                          "border-border bg-card",
                      )}
                    >
                      <p className="text-sm font-medium capitalize">
                        {t("kanban:detail.qaStatus", {
                          status: task.qaReport.status,
                        })}
                      </p>
                      {task.qaReport.issues && task.qaReport.issues.length > 0 && (
                        <ul className="mt-2 space-y-1">
                          {task.qaReport.issues.map((issue) => (
                            <li
                              key={issue.id}
                              className="text-xs text-muted-foreground flex items-start gap-1"
                            >
                              <span
                                className={cn(
                                  "shrink-0 mt-0.5 h-1.5 w-1.5 rounded-full",
                                  issue.severity === "critical" && "bg-red-500",
                                  issue.severity === "major" && "bg-orange-500",
                                  issue.severity === "minor" && "bg-yellow-500",
                                )}
                              />
                              {issue.description}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                )}

                {/* PR Link */}
                {task.metadata?.prUrl && (
                  <a
                    href={task.metadata.prUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 rounded-lg border border-border p-3 hover:bg-accent transition-colors"
                  >
                    <GitPullRequest className="h-4 w-4 text-green-500" />
                    <span className="text-sm">
                      {t("kanban:detail.viewPullRequest")}
                    </span>
                    <ExternalLink className="h-3 w-3 text-muted-foreground ml-auto" />
                  </a>
                )}
              </TabsContent>

              {/* Subtasks Tab */}
              <TabsContent value="subtasks" className="mt-4">
                <TaskSubtasks task={task} />
              </TabsContent>

              {/* Files Tab */}
              <TabsContent value="files" className="mt-4">
                <TaskFiles task={task} />
              </TabsContent>

              {/* Logs Tab */}
              <TabsContent value="logs" className="mt-4">
                <TaskLogs task={task} />
              </TabsContent>

              {/* Review Tab */}
              <TabsContent value="review" className="mt-4">
                <TaskReview task={task} />
              </TabsContent>
            </div>
          </Tabs>

          {/* Footer Actions */}
          <Separator />
          <div className="p-4">
            <TaskActions
              task={task}
              isStuck={isStuck}
              onStart={onStart ? () => onStart(task.id) : undefined}
              onStop={onStop ? () => onStop(task.id) : undefined}
            />
          </div>
        </TooltipProvider>
      </div>
    </div>
  );
}
