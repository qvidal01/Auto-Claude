"use client";

/**
 * PhaseProgressIndicator - Execution phase progress bar
 *
 * Displays progress for the current execution phase (planning, coding, QA, etc.).
 * Adapts between indeterminate (planning/QA) and determinate (coding) progress modes.
 * Web port of the Electron PhaseProgressIndicator.
 */

import { memo, useRef, useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui/utils";
import { Progress } from "@auto-claude/ui/primitives";
import type { ExecutionPhase, Subtask } from "@auto-claude/types";

interface PhaseProgressIndicatorProps {
  phase?: ExecutionPhase;
  subtasks: Subtask[];
  /** Fallback progress percentage (0-100) when phase logs unavailable */
  phaseProgress?: number;
  isStuck?: boolean;
  isRunning?: boolean;
  className?: string;
}

/** Phase display configuration (colors only - labels are translated) */
const PHASE_COLORS: Record<ExecutionPhase, { color: string; bgColor: string }> = {
  idle: { color: "bg-muted-foreground", bgColor: "bg-muted" },
  planning: { color: "bg-amber-500", bgColor: "bg-amber-500/20" },
  coding: { color: "bg-info", bgColor: "bg-info/20" },
  rate_limit_paused: { color: "bg-orange-500", bgColor: "bg-orange-500/20" },
  auth_failure_paused: { color: "bg-red-500", bgColor: "bg-red-500/20" },
  qa_review: { color: "bg-purple-500", bgColor: "bg-purple-500/20" },
  qa_fixing: { color: "bg-orange-500", bgColor: "bg-orange-500/20" },
  complete: { color: "bg-success", bgColor: "bg-success/20" },
  failed: { color: "bg-destructive", bgColor: "bg-destructive/20" },
};

/** Phase label translation keys */
const PHASE_LABEL_KEYS: Record<ExecutionPhase, string> = {
  idle: "common:labels.idle",
  planning: "common:labels.planning",
  coding: "common:labels.coding",
  rate_limit_paused: "common:labels.rateLimitPaused",
  auth_failure_paused: "common:labels.authFailurePaused",
  qa_review: "common:labels.reviewing",
  qa_fixing: "common:labels.fixing",
  complete: "common:labels.complete",
  failed: "common:labels.failed",
};

export const PhaseProgressIndicator = memo(function PhaseProgressIndicator({
  phase: rawPhase,
  subtasks,
  phaseProgress,
  isStuck = false,
  isRunning = false,
  className,
}: PhaseProgressIndicatorProps) {
  const { t } = useTranslation("common");
  const phase = rawPhase || "idle";
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(true);

  // Use IntersectionObserver to pause animations when not visible
  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => setIsVisible(entry.isIntersecting),
      { threshold: 0.1 },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const shouldAnimate = isVisible && isRunning && !isStuck;

  // Calculate subtask-based progress (for coding phase)
  const completedSubtasks = subtasks.filter((s) => s.status === "completed").length;
  const totalSubtasks = subtasks.length;
  const subtaskProgress = totalSubtasks > 0 ? Math.round((completedSubtasks / totalSubtasks) * 100) : 0;

  const isIndeterminatePhase = phase === "planning" || phase === "qa_review" || phase === "qa_fixing";
  const showSubtaskProgress = totalSubtasks > 0;

  const colors = PHASE_COLORS[phase] || PHASE_COLORS.idle;
  const phaseLabel = t(PHASE_LABEL_KEYS[phase] || PHASE_LABEL_KEYS.idle);

  // Determine displayed progress value
  const displayProgress = showSubtaskProgress
    ? subtaskProgress
    : isRunning && isIndeterminatePhase && (phaseProgress ?? 0) > 0
      ? Math.round(Math.min(phaseProgress!, 100))
      : null;

  return (
    <div ref={containerRef} className={cn("space-y-1.5", className)}>
      {/* Progress label row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {isStuck ? t("labels.interrupted", "Interrupted") : showSubtaskProgress ? t("labels.progress", "Progress") : phaseLabel}
          </span>
          {/* Activity indicator dot for indeterminate phases */}
          {isRunning && !isStuck && isIndeterminatePhase && (
            <div
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                colors.color,
                shouldAnimate && "animate-pulse",
              )}
            />
          )}
        </div>
        <span className="text-xs font-medium text-foreground">
          {displayProgress !== null ? `${displayProgress}%` : "\u2014"}
        </span>
      </div>

      {/* Progress bar */}
      <div
        className={cn(
          "relative h-1.5 w-full overflow-hidden rounded-full",
          isStuck ? "bg-warning/20" : "bg-border",
        )}
      >
        {isStuck ? (
          <div className="absolute inset-0 animate-pulse bg-warning/40" />
        ) : showSubtaskProgress ? (
          <div
            className={cn("h-full rounded-full transition-all duration-500 ease-out", colors.color)}
            style={{ width: `${subtaskProgress}%` }}
          />
        ) : shouldAnimate && isIndeterminatePhase ? (
          <div
            className={cn(
              "absolute h-full w-1/3 rounded-full animate-[indeterminate_1.5s_ease-in-out_infinite]",
              colors.color,
            )}
          />
        ) : (
          <div
            className={cn("h-full rounded-full", colors.color)}
            style={{ width: `${displayProgress ?? 0}%` }}
          />
        )}
      </div>
    </div>
  );
});
