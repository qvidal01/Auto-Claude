"use client";

import { useTranslation } from "react-i18next";
import { FileText, FilePlus, FileEdit } from "lucide-react";
import { cn, Badge } from "@auto-claude/ui";
import type { Task } from "@auto-claude/types";

interface TaskFilesProps {
  task: Task;
}

export function TaskFiles({ task }: TaskFilesProps) {
  const { t } = useTranslation(["kanban"]);

  // Collect all files from subtasks
  const allFiles = new Map<string, "created" | "modified">();
  for (const subtask of task.subtasks) {
    if (subtask.files) {
      for (const file of subtask.files) {
        if (!allFiles.has(file)) {
          allFiles.set(file, "modified");
        }
      }
    }
  }

  if (allFiles.size === 0) {
    return (
      <div className="text-sm text-muted-foreground text-center py-8">
        {t("kanban:detail.noFiles", "No files associated with this task")}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {t("kanban:detail.filesCount", "{{count}} files", {
          count: allFiles.size,
        })}
      </p>
      <div className="space-y-1">
        {Array.from(allFiles.entries()).map(([file, status]) => (
          <div
            key={file}
            className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm"
          >
            {status === "created" ? (
              <FilePlus className="h-4 w-4 text-green-500 shrink-0" />
            ) : (
              <FileEdit className="h-4 w-4 text-blue-500 shrink-0" />
            )}
            <span className="font-mono text-xs truncate flex-1">{file}</span>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px]",
                status === "created" ? "text-green-600" : "text-blue-600",
              )}
            >
              {status}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}
