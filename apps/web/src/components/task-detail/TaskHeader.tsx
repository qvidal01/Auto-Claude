"use client";

import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { X, Pencil, AlertTriangle } from "lucide-react";
import { cn, Button, Badge, Tooltip, TooltipContent, TooltipTrigger } from "@auto-claude/ui";
import type { Task } from "@auto-claude/types";

interface TaskHeaderProps {
  task: Task;
  isStuck: boolean;
  isIncomplete: boolean;
  taskProgress: { completed: number; total: number };
  isRunning: boolean;
  onClose: () => void;
  onEdit: () => void;
}

export function TaskHeader({
  task,
  isStuck,
  isIncomplete,
  taskProgress,
  isRunning,
  onClose,
  onEdit,
}: TaskHeaderProps) {
  const { t } = useTranslation(["kanban", "common"]);

  const displayTitle = useMemo(() => task.title, [task.title]);

  return (
    <div className="flex items-start justify-between p-4 pb-3">
      <div className="flex-1 min-w-0 pr-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <h2 className="font-semibold text-lg text-foreground line-clamp-2 leading-snug cursor-default">
              {displayTitle}
            </h2>
          </TooltipTrigger>
          {displayTitle.length > 40 && (
            <TooltipContent side="bottom" className="max-w-xs">
              <p className="text-sm">{displayTitle}</p>
            </TooltipContent>
          )}
        </Tooltip>
        <div className="mt-2 flex items-center gap-2 flex-wrap">
          <Badge variant="outline" className="text-xs font-mono">
            {task.specId}
          </Badge>
          {isStuck ? (
            <Badge variant="destructive" className="text-xs flex items-center gap-1 animate-pulse">
              <AlertTriangle className="h-3 w-3" />
              {t("kanban:card.stuck")}
            </Badge>
          ) : isIncomplete ? (
            <>
              <Badge variant="destructive" className="text-xs flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                {t("kanban:detail.incomplete", "Incomplete")}
              </Badge>
              <Badge variant="outline" className="text-xs text-orange-400">
                {taskProgress.completed}/{taskProgress.total} subtasks
              </Badge>
            </>
          ) : (
            <Badge
              variant={
                task.status === "done"
                  ? "default"
                  : task.status === "human_review"
                    ? "secondary"
                    : task.status === "in_progress"
                      ? "default"
                      : "outline"
              }
              className={cn(
                "text-xs",
                task.status === "done" && "bg-green-500/10 text-green-600",
                task.status === "in_progress" && "bg-yellow-500/10 text-yellow-600",
                task.status === "human_review" && "bg-purple-500/10 text-purple-600",
                task.status === "error" && "bg-red-500/10 text-red-600",
              )}
            >
              {t(`kanban:columns.${task.status}`, task.status)}
            </Badge>
          )}
          {task.status === "human_review" && task.reviewReason && (
            <Badge
              variant="outline"
              className={cn(
                "text-xs",
                task.reviewReason === "completed" && "text-green-600",
                task.reviewReason === "errors" && "text-red-600",
              )}
            >
              {t(`kanban:card.review.${task.reviewReason}`, task.reviewReason)}
            </Badge>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1 shrink-0 -mr-1 -mt-1">
        <Tooltip>
          <TooltipTrigger asChild>
            <span>
              <Button
                variant="ghost"
                size="icon"
                className="hover:bg-primary/10 hover:text-primary transition-colors"
                onClick={onEdit}
                disabled={isRunning && !isStuck}
              >
                <Pencil className="h-4 w-4" />
              </Button>
            </span>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            {isRunning && !isStuck
              ? t("kanban:detail.cannotEditWhileRunning", "Cannot edit while running")
              : t("kanban:detail.editTask", "Edit task")}
          </TooltipContent>
        </Tooltip>
        <Button
          variant="ghost"
          size="icon"
          className="hover:bg-destructive/10 hover:text-destructive transition-colors"
          onClick={onClose}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
