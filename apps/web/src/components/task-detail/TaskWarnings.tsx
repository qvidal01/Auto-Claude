"use client";

import { useTranslation } from "react-i18next";
import { AlertTriangle, AlertCircle, Info } from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { Task } from "@auto-claude/types";

interface TaskWarningsProps {
  task: Task;
  isStuck?: boolean;
  error?: string | null;
}

export function TaskWarnings({ task, isStuck = false, error }: TaskWarningsProps) {
  const { t } = useTranslation(["kanban"]);

  const warnings: Array<{
    type: "error" | "warning" | "info";
    message: string;
  }> = [];

  if (isStuck) {
    warnings.push({
      type: "warning",
      message: t(
        "kanban:detail.stuckWarning",
        "This task appears to be stuck. It may need to be recovered or restarted.",
      ),
    });
  }

  if (task.status === "error") {
    warnings.push({
      type: "error",
      message: t(
        "kanban:detail.errorWarning",
        "This task encountered an error during execution.",
      ),
    });
  }

  if (error) {
    warnings.push({
      type: "error",
      message: error,
    });
  }

  // QA issues
  if (task.qaReport?.status === "failed" && task.qaReport.issues.length > 0) {
    for (const issue of task.qaReport.issues) {
      warnings.push({
        type: issue.severity === "critical" ? "error" : issue.severity === "major" ? "warning" : "info",
        message: issue.description,
      });
    }
  }

  if (warnings.length === 0) return null;

  return (
    <div className="space-y-2">
      {warnings.map((warning, index) => {
        const Icon =
          warning.type === "error"
            ? AlertCircle
            : warning.type === "warning"
              ? AlertTriangle
              : Info;

        return (
          <div
            key={index}
            className={cn(
              "flex items-start gap-2 rounded-md border p-3",
              warning.type === "error" &&
                "border-destructive/30 bg-destructive/5 text-destructive",
              warning.type === "warning" &&
                "border-warning/30 bg-warning/5 text-warning",
              warning.type === "info" &&
                "border-info/30 bg-info/5 text-info",
            )}
          >
            <Icon className="h-4 w-4 mt-0.5 shrink-0" />
            <p className="text-xs">{warning.message}</p>
          </div>
        );
      })}
    </div>
  );
}
