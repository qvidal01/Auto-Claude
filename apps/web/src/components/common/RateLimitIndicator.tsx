"use client";

/**
 * RateLimitIndicator - Rate limit warning badge
 *
 * Shows a warning badge when the user is approaching or has hit rate limits.
 * Web port of the rate limit display from the Electron app.
 */

import { AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@auto-claude/ui/primitives/tooltip";
import { Badge } from "@auto-claude/ui/primitives/badge";

interface RateLimitIndicatorProps {
  /** Whether a rate limit is currently active */
  isRateLimited: boolean;
  /** Type of rate limit hit */
  limitType?: "session" | "weekly";
  /** When the limit resets (human-readable) */
  resetTime?: string;
  className?: string;
}

export function RateLimitIndicator({
  isRateLimited,
  limitType,
  resetTime,
  className,
}: RateLimitIndicatorProps) {
  const { t } = useTranslation("common");

  if (!isRateLimited) {
    return null;
  }

  const limitLabel = limitType === "weekly"
    ? t("labels.weeklyLimit", "Weekly limit")
    : t("labels.sessionLimit", "Session limit");

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              "flex items-center gap-1.5 rounded-md border px-2.5 py-1.5",
              "bg-red-500/10 text-red-500 border-red-500/20",
              className,
            )}
          >
            <AlertTriangle className="h-3.5 w-3.5 animate-pulse" />
            <span className="text-xs font-semibold">
              {t("labels.rateLimited", "Rate Limited")}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs max-w-xs">
          <div className="space-y-1">
            <div className="font-medium text-red-500">{limitLabel}</div>
            {resetTime && (
              <div className="text-muted-foreground">
                {t("labels.resetsAt", "Resets: {{time}}", { time: resetTime })}
              </div>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
