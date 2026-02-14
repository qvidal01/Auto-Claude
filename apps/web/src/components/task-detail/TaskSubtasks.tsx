"use client";

import { useTranslation } from "react-i18next";
import { CheckCircle2, Clock, AlertCircle, FileText } from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { Task } from "@auto-claude/types";

interface TaskSubtasksProps {
  task: Task;
}

export function TaskSubtasks({ task }: TaskSubtasksProps) {
  const { t } = useTranslation(["kanban"]);

  if (!task.subtasks || task.subtasks.length === 0) return null;

  const completed = task.subtasks.filter((s) => s.status === "completed").length;

  return (
    <div>
      <h3 className="text-sm font-medium mb-2">
        {t("kanban:detail.subtasks", {
          completed,
          total: task.subtasks.length,
        })}
      </h3>
      <div className="space-y-2">
        {task.subtasks.map((subtask) => (
          <div
            key={subtask.id}
            className={cn(
              "flex items-start gap-2 rounded-md border border-border p-3",
              subtask.status === "completed" && "bg-green-500/5",
              subtask.status === "failed" && "bg-red-500/5",
              subtask.status === "in_progress" && "bg-yellow-500/5",
            )}
          >
            {subtask.status === "completed" ? (
              <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
            ) : subtask.status === "failed" ? (
              <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
            ) : subtask.status === "in_progress" ? (
              <Clock className="h-4 w-4 text-yellow-500 mt-0.5 shrink-0 animate-pulse" />
            ) : (
              <Clock className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">{subtask.title}</p>
              {subtask.description && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  {subtask.description}
                </p>
              )}
              {subtask.files && subtask.files.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {subtask.files.map((file) => (
                    <span
                      key={file}
                      className="inline-flex items-center gap-1 rounded bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground"
                    >
                      <FileText className="h-2.5 w-2.5" />
                      {file.split("/").pop()}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
