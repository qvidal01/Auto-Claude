"use client";

/**
 * UsageIndicator - Real-time Claude usage display
 *
 * Displays current session/weekly usage as a badge with color-coded status.
 * Web port of the Electron UsageIndicator - uses REST API instead of IPC.
 */

import { useState, useEffect, useCallback } from "react";
import { Activity, AlertCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@auto-claude/ui/primitives/tooltip";
import { Badge } from "@auto-claude/ui/primitives/badge";
import type { ClaudeUsageSnapshot } from "@auto-claude/types";

/** Usage threshold constants for color coding */
const THRESHOLD_CRITICAL = 95;
const THRESHOLD_WARNING = 91;
const THRESHOLD_ELEVATED = 71;

function getColorClass(percent: number): string {
  if (percent >= THRESHOLD_CRITICAL) return "text-red-500";
  if (percent >= THRESHOLD_WARNING) return "text-orange-500";
  if (percent >= THRESHOLD_ELEVATED) return "text-yellow-500";
  return "text-green-500";
}

function getBadgeColorClasses(percent: number): string {
  if (percent >= THRESHOLD_CRITICAL) return "text-red-500 bg-red-500/10 border-red-500/20";
  if (percent >= THRESHOLD_WARNING) return "text-orange-500 bg-orange-500/10 border-orange-500/20";
  if (percent >= THRESHOLD_ELEVATED) return "text-yellow-500 bg-yellow-500/10 border-yellow-500/20";
  return "text-green-500 bg-green-500/10 border-green-500/20";
}

function getBarColorClass(percent: number): string {
  if (percent >= THRESHOLD_CRITICAL) return "bg-red-500";
  if (percent >= THRESHOLD_WARNING) return "bg-orange-500";
  if (percent >= THRESHOLD_ELEVATED) return "bg-yellow-500";
  return "bg-green-500";
}

interface UsageIndicatorProps {
  /** Optional usage snapshot (if managed externally). Otherwise fetches its own. */
  usage?: ClaudeUsageSnapshot | null;
  className?: string;
}

export function UsageIndicator({ usage: externalUsage, className }: UsageIndicatorProps) {
  const { t } = useTranslation("common");
  const [usage, setUsage] = useState<ClaudeUsageSnapshot | null>(externalUsage ?? null);
  const [isLoading, setIsLoading] = useState(!externalUsage);

  // Sync external usage if provided
  useEffect(() => {
    if (externalUsage !== undefined) {
      setUsage(externalUsage);
      setIsLoading(false);
    }
  }, [externalUsage]);

  if (isLoading || !usage) {
    return null;
  }

  const maxPercent = Math.max(usage.sessionPercent, usage.weeklyPercent);
  const colorClass = getColorClass(maxPercent);
  const badgeClasses = getBadgeColorClasses(maxPercent);

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className={cn(
              "flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 transition-all hover:opacity-80",
              badgeClasses,
              className,
            )}
            aria-label={t("labels.usage", "Usage: {{percent}}%", { percent: Math.round(maxPercent) })}
          >
            <Activity className={cn("h-3.5 w-3.5", colorClass)} />
            <span className="text-xs font-semibold">{Math.round(maxPercent)}%</span>
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs max-w-xs">
          <div className="space-y-2 p-1">
            <div className="font-medium text-foreground">{t("labels.usageBreakdown", "Usage Breakdown")}</div>

            {/* Session usage */}
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted-foreground">{t("labels.session", "Session")}</span>
                <span className={cn("font-semibold", getColorClass(usage.sessionPercent))}>
                  {Math.round(usage.sessionPercent)}%
                </span>
              </div>
              <div className="h-1 w-full overflow-hidden rounded-full bg-border">
                <div
                  className={cn("h-full rounded-full transition-all", getBarColorClass(usage.sessionPercent))}
                  style={{ width: `${Math.min(usage.sessionPercent, 100)}%` }}
                />
              </div>
            </div>

            {/* Weekly usage */}
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted-foreground">{t("labels.weekly", "Weekly")}</span>
                <span className={cn("font-semibold", getColorClass(usage.weeklyPercent))}>
                  {Math.round(usage.weeklyPercent)}%
                </span>
              </div>
              <div className="h-1 w-full overflow-hidden rounded-full bg-border">
                <div
                  className={cn("h-full rounded-full transition-all", getBarColorClass(usage.weeklyPercent))}
                  style={{ width: `${Math.min(usage.weeklyPercent, 100)}%` }}
                />
              </div>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
