"use client";

import { useTranslation } from "react-i18next";
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { IdeationType, IdeationTypeState } from "@/stores/ideation-store";

const TYPE_LABELS: Record<IdeationType, string> = {
  code_improvements: "Code Improvements",
  ui_ux_improvements: "UI/UX Improvements",
  documentation_gaps: "Documentation Gaps",
  security_hardening: "Security Hardening",
  performance_optimizations: "Performance Optimizations",
  code_quality: "Code Quality",
};

interface GenerationProgressProps {
  typeStates: Record<IdeationType, IdeationTypeState>;
  logs: string[];
  progress: number;
  message: string;
}

export function GenerationProgress({
  typeStates,
  logs,
  progress,
  message,
}: GenerationProgressProps) {
  const { t } = useTranslation("views");

  const typeEntries = Object.entries(typeStates) as [IdeationType, IdeationTypeState][];
  const completedCount = typeEntries.filter(([, s]) => s === "completed").length;
  const totalCount = typeEntries.length;

  return (
    <div className="flex h-full flex-col items-center justify-center p-8">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
          <h2 className="mt-4 text-lg font-semibold">
            {t("ideation.generatingTitle")}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {message || t("ideation.generatingDescription")}
          </p>
        </div>

        {/* Overall progress bar */}
        <div>
          <div className="mb-1.5 flex items-center justify-between text-xs text-muted-foreground">
            <span>{t("ideation.progress")}</span>
            <span>
              {completedCount}/{totalCount}
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Per-type status */}
        <div className="space-y-2">
          {typeEntries.map(([type, state]) => (
            <div
              key={type}
              className="flex items-center gap-3 rounded-md border border-border p-2.5"
            >
              {state === "pending" && (
                <Clock className="h-4 w-4 text-muted-foreground" />
              )}
              {state === "generating" && (
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
              )}
              {state === "completed" && (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              )}
              {state === "failed" && (
                <XCircle className="h-4 w-4 text-red-500" />
              )}
              <span
                className={cn(
                  "flex-1 text-sm",
                  state === "completed" && "text-muted-foreground",
                  state === "failed" && "text-red-500",
                )}
              >
                {TYPE_LABELS[type]}
              </span>
              <span className="text-[11px] text-muted-foreground capitalize">
                {state}
              </span>
            </div>
          ))}
        </div>

        {/* Log output */}
        {logs.length > 0 && (
          <div className="max-h-32 overflow-y-auto rounded-md border border-border bg-secondary/50 p-3">
            {logs.slice(-10).map((log, idx) => (
              <p key={idx} className="text-[11px] text-muted-foreground font-mono">
                {log}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
